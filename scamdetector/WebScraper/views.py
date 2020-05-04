from django.shortcuts import render
from bs4 import BeautifulSoup
import requests
from requests.compat import quote_plus
from . import models
import io
import os
import argparse
import asyncio
import urllib.request
from multiprocessing.dummy import Pool as ThreadPool
import time
# Imports the Google Cloud client library
# [START vision_python_migration_import]
from google.cloud import vision
from google.cloud.vision import types
from google.cloud import storage
# [END vision_python_migration_import]

GS_BUCKET_NAME = "craigslist-images-bucket"

# Create your views here.
def home(request):
    return render(request, 'WebScraper/index.html')

def new_search(request):
    # Get search object
    search_url = request.POST.get('search_url')

    # Check is text is null or not
    if search_url == None:
        search_url = ''

    # save searchs in the table
    models.Search.objects.create(search=search_url)
    # Format Query
    final_url = search_url

    # Excute the query
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    }
    response = requests.get(final_url, verify=False, headers=headers)
    # Reponse from query
    data = response.text
    # Clean up the results using beautiful soup
    soup = BeautifulSoup(data, features='html.parser')
    post_full_title = soup.find(class_="postingtitletext").text
    post_description = soup.find(id = "postingbody").text.replace("QR Code Link to This Post","")
    if soup.find(class_="price"):
        post_price = soup.find(class_="price").text
    else:
        post_price = "N/A"

    for post in soup.find_all('div', "swipe-wrap"):
        for post_content in post.find_all('div', "slide"):
            for pic in post_content.find_all("img"):
                first_img_url = pic['src']

    # Get all the images from the craigslist ad
    post_image = []
    for img in soup.find_all('div', id="thumbs"):
        for img_content in img.find_all("a", "thumb"):
            post_image.append(img_content['href'])

    # Make the Pool of workers
    pool = ThreadPool(8)
    # Upload the images in their own threads
    # and return the results
    results = pool.map(upload_blob, post_image)
    # start a time to measure the performance
    start_time = time.time()
    #close the pool and wait for the work to finish
    pool.close()
    pool.join()
    print('M1 Time taken: {}'.format(time.time() - start_time))

    gs_path = []
    for img in results:
        gs_path.append("gs://{}/{}".format(GS_BUCKET_NAME, img))

    # Upload all the images to google cloud storage
    # for image in post_image:
    #     print("Uploading images to google cloud storage .....")
    #     gcs_path = upload_blob(image)
    #     print("Sending request to google cloud api .....")
    #     print(gcs_path)
    #     #annotate_results_from_api.append(
    #         #report(annotate("gs://{}/{}".format(GS_BUCKET_NAME, gcs_path))))
    
    pool = ThreadPool(8)
    images_match = pool.starmap(annotate, zip(gs_path, post_image))
    start_time = time.time()
    pool.close()
    pool.join()
    print('M2 Time taken: {}'.format(time.time() - start_time))
    #print(post_image)
    #print(annotate_results_from_api)
    print(images_match)

    search_dictionary = {
        'search': final_url,
        'post_full_title': post_full_title,
        'post_price': post_price,
        'first_img_url': first_img_url,
        'post_image': post_image,
        'post_description': post_description,
        'no_of_images': len(post_image),
        'images_match': images_match
    }
    return render(request, 'WebScraper/results.html', search_dictionary)

def run_quickstart():
    # [START vision_quickstart]

    # Instantiates a client
    # [START vision_python_migration_client]
    client = vision.ImageAnnotatorClient()
    # [END vision_python_migration_client]

    # The name of the image file to annotate
    file_name = os.path.abspath('resources/wakeupcat.jpg')

    # Loads the image into memory
    with io.open(file_name, 'rb') as image_file:
        content = image_file.read()

    image = types.Image(content=content)

    # Performs label detection on the image file
    response = client.label_detection(image=image)
    labels = response.label_annotations

    print('Labels:')
    for label in labels:
        print(label.description)
        print(label.score)
    # [END vision_quickstart]
# run_quickstart()

# [START vision_web_detection_gcs]

def detect_web_uri(uri):
    """Detects web annotations in the file located in Google Cloud Storage."""
    client = vision.ImageAnnotatorClient()
    image = vision.types.Image()
    image.source.image_uri = uri

    response = client.web_detection(image=image)
    annotations = response.web_detection

    if annotations.best_guess_labels:
        for label in annotations.best_guess_labels:
            print('\nBest guess label: {}'.format(label.label))

    if annotations.pages_with_matching_images:
        print('\n{} Pages with matching images found:'.format(
            len(annotations.pages_with_matching_images)))

        for page in annotations.pages_with_matching_images:
            print('\n\tPage url   : {}'.format(page.url))

            if page.full_matching_images:
                print('\t{} Full Matches found: '.format(
                    len(page.full_matching_images)))

                for image in page.full_matching_images:
                    print('\t\tImage url  : {}'.format(image.url))

            if page.partial_matching_images:
                print('\t{} Partial Matches found: '.format(
                    len(page.partial_matching_images)))

                for image in page.partial_matching_images:
                    print('\t\tImage url  : {}'.format(image.url))

    if annotations.web_entities:
        print('\n{} Web entities found: '.format(
            len(annotations.web_entities)))

        for entity in annotations.web_entities:
            print('\n\tScore      : {}'.format(entity.score))
            print(u'\tDescription: {}'.format(entity.description))

    if annotations.visually_similar_images:
        print('\n{} visually similar images found:\n'.format(
            len(annotations.visually_similar_images)))

        for image in annotations.visually_similar_images:
            print('\tImage url    : {}'.format(image.url))

    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))
# [END vision_web_detection_gcs]


def annotate(path, web_path):
    """Returns web annotations given the path to an image."""
    # [START vision_web_detection_tutorial_annotate]
    client = vision.ImageAnnotatorClient()
    if path.startswith('http') or path.startswith('gs:') or path.startswith('https'):
        image = types.Image()
        image.source.image_uri = path
    else:
        with io.open(path, 'rb') as image_file:
            content = image_file.read()

        image = types.Image(content=content)

    annotations = client.web_detection(image=image).web_detection
    # [END vision_web_detection_tutorial_annotate]

    pages_with_matching_images = {}
    full_matching_images = {}
    partial_matching_images = {}
    #print(annotations)
    if annotations.pages_with_matching_images:
        counter = 0
        for page in annotations.pages_with_matching_images:
            #print(page)
            pages_with_matching_images[counter] = page.partial_matching_images
            counter +=1

    if annotations.full_matching_images:
        i = 1
        full_matching_images[web_path] = {}
        for image in annotations.full_matching_images:
            if image.url:
                full_matching_images[web_path].update({str(i) : image.url})
                #print(full_matching_images[path])
                i +=1
    else:
        full_matching_images[web_path] = ""

    if annotations.partial_matching_images:
        counter = 0
        for image in annotations.partial_matching_images:
            partial_matching_images[counter] = image
            counter +=1

    #print(pages_with_matching_images)
    # print(full_matching_images)
   # print("legth ", len(full_matching_images))
    #print(partial_matching_images)
    # print(partial_matching_images)
    # print(full_matching_images)
    return full_matching_images

def report(annotations):
    """Prints detected features in the provided web annotations."""
    # [START vision_web_detection_tutorial_print_annotations]
    pages_with_matching_images = []
    full_matching_images = []
    partial_matching_images = []

    if annotations.pages_with_matching_images:
        print('\n{} Pages with matching images retrieved'.format(
            len(annotations.pages_with_matching_images)))

        for page in annotations.pages_with_matching_images:
            print('Url   : {}'.format(page.url))
            pages_with_matching_images.append(page)

    if annotations.full_matching_images:
        print('\n{} Full Matches found: '.format(
              len(annotations.full_matching_images)))

        for image in annotations.full_matching_images:
            print('Url  : {}'.format(image.url))
            full_matching_images.append(image)

    if annotations.partial_matching_images:
        print('\n{} Partial Matches found: '.format(
              len(annotations.partial_matching_images)))

        for image in annotations.partial_matching_images:
            print('Url  : {}'.format(image.url))
            partial_matching_images.append(image)

    if annotations.web_entities:
        print('\n{} Web entities found: '.format(
              len(annotations.web_entities)))

        for entity in annotations.web_entities:
            print('Score      : {}'.format(entity.score))
            print('Description: {}'.format(entity.description))

    api_result = {
        'pages_with_matching_images': pages_with_matching_images,
        'full_matching_images': full_matching_images,
        'partial_matching_images': partial_matching_images
    }
    return api_result
    # [END vision_web_detection_tutorial_print_annotations]

# Retrieved from https://stackoverflow.com/questions/54235721/transfer-file-from-url-to-cloud-storage


def upload_blob(source_file_name):
    file = urllib.request.urlopen(source_file_name)
    firstpos = source_file_name.rfind("/")
    lastpos = len(source_file_name)
    destination_blob_name = source_file_name[firstpos+1:lastpos]
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(GS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(file.read(), content_type='image/jpg')
    return destination_blob_name
