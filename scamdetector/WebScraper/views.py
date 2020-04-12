from django.shortcuts import render
from bs4 import BeautifulSoup
import requests
from requests.compat import quote_plus
from . import models
import io
import os
import argparse

# Imports the Google Cloud client library
# [START vision_python_migration_import]
from google.cloud import vision
from google.cloud.vision import types
# [END vision_python_migration_import]
BASE_QUERY = 'https://minneapolis.craigslist.org/search/sss?query={}&sort=rel'
min_price_query = '&min_price={}'
max_price_query = '&max_price={}'
Image_URL = 'https://images.craigslist.org/{}_300x300.jpg'

# Create your views here.
def home(request):
    return render(request , 'WebScraper/index.html')

def new_search(request):
    #Get search object
    search_url = request.POST.get('search_url')
    
    #Check is text is null or not
    if search_url == None:
        search_url = ''

    #save searchs in the table
    models.Search.objects.create(search = search_url)
    #Format Query
    #final_url =  BASE_QUERY.format(quote_plus(Search_text))
    final_url = search_url
    '''
    if min_text != '' and max_text != '':
        final_url = final_url + min_price_query.format(min_text) + max_price_query.format(max_text)
    elif (min_text != '' and max_text == ''):
        final_url = final_url + min_price_query.format(min_text)
    elif (min_text == '' and max_text != ''):
        final_url = final_url + max_price_query.format(max_text)
    '''
    print(final_url)
    #Excute the query
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    }
    response = requests.get(final_url, verify=False, headers=headers)
    #Reponse from query
    data = response.text
    #Clean up the results using beautiful soup
    soup = BeautifulSoup(data, features='html.parser')
    #post_lists = soup.find_all( 'li',{'class' : 'result-row'})
    #post_title = soup.find(class_ = "postingtitletext").text
    post_full_title = soup.find(class_ = "postingtitletext").text
    print(post_full_title)

    if soup.find(class_ = "price"):
        post_price = soup.find(class_ = "price").text
    else:
        post_price = "N/A"

    # if soup.find(class_ = "first").get('data-imgid'):
    #     first_img_id = soup.find(class_ = "first").get('data-imgid').text
    #     img_src = soup.find("data-imgid"=first_img_id).text
    #     print(img_src)
    # else:
    #     first_img_id = ''

    for post in soup.find_all('div', "swipe-wrap"):
        for post_content in post.find_all('div', "slide"):
            for pic in post_content.find_all("img"):
                print(pic['src'])
                first_img_url = pic['src']
                print(first_img_url)

    for img in soup.find_all('div', id="thumbs"):
        for img_content in img.find_all("img"):
            post_image = Image_URL.format(img_content['src'])
    print(post_price)
    #post_image_URL = soup.find(class_ = 'result-image').get('data-ids').split(',')[0].split(':')[1]

    #print(post_image_URL.text)
    '''for post in post_lists:
        print(post)
        post_title = post.find(class_  ='result-title hdrlnk').text
        post_link  = post.find('a').get('href')

        if post.find(class_  = 'result-price'):
            post_cost  = post.find(class_  = 'result-price').text
        else:
            post_cost = 'NA'
        if post.find(class_ = 'result-image').get('data-ids'):
            post_image_URL = post.find(class_ = 'result-image').get('data-ids').split(',')[0].split(':')[1]
            post_image = Image_URL.format(post_image_URL)
        else:
            post_image = 'https://image.shutterstock.com/image-vector/no-image-available-icon-vector-260nw-1323742826.jpg'
        final_posts.append((post_title, post_link, post_cost,post_image ))
        numberofsearches+=1
    '''
    
    search_dictionary ={
        'search' : final_url,
        'post_full_title': post_full_title,
        'post_price': post_price,
        'first_img_url': first_img_url
    }
    return render(request , 'WebScraper/results.html',search_dictionary)

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
run_quickstart()

# [START vision_web_detection_gcs]
def detect_web_uri(uri):
    """Detects web annotations in the file located in Google Cloud Storage."""
    from google.cloud import vision
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
#detect_web_uri("gs://cloud-samples-data/vision/web/carnaval.jpeg")
#detect_web_uri("gs://cloud-samples-data/vision/label/setagaya.jpeg")

# [START vision_web_detection_tutorial]
# [START vision_web_detection_tutorial_imports]
import argparse
import io

from google.cloud import vision
from google.cloud.vision import types
# [END vision_web_detection_tutorial_imports]


def annotate(path):
    """Returns web annotations given the path to an image."""
    # [START vision_web_detection_tutorial_annotate]
    client = vision.ImageAnnotatorClient()

    if path.startswith('http') or path.startswith('gs:'):
        image = types.Image()
        image.source.image_uri = path

    else:
        with io.open(path, 'rb') as image_file:
            content = image_file.read()

        image = types.Image(content=content)

    web_detection = client.web_detection(image=image).web_detection
    # [END vision_web_detection_tutorial_annotate]

    return web_detection


def report(annotations):
    """Prints detected features in the provided web annotations."""
    # [START vision_web_detection_tutorial_print_annotations]
    if annotations.pages_with_matching_images:
        print('\n{} Pages with matching images retrieved'.format(
            len(annotations.pages_with_matching_images)))

        for page in annotations.pages_with_matching_images:
            print('Url   : {}'.format(page.url))

    if annotations.full_matching_images:
        print('\n{} Full Matches found: '.format(
              len(annotations.full_matching_images)))

        for image in annotations.full_matching_images:
            print('Url  : {}'.format(image.url))

    if annotations.partial_matching_images:
        print('\n{} Partial Matches found: '.format(
              len(annotations.partial_matching_images)))

        for image in annotations.partial_matching_images:
            print('Url  : {}'.format(image.url))

    if annotations.web_entities:
        print('\n{} Web entities found: '.format(
              len(annotations.web_entities)))

        for entity in annotations.web_entities:
            print('Score      : {}'.format(entity.score))
            print('Description: {}'.format(entity.description))
    # [END vision_web_detection_tutorial_print_annotations]


# if __name__ == '__main__':
#     # [START vision_web_detection_tutorial_run_application]
#     parser = argparse.ArgumentParser(
#         description=__doc__,
#         formatter_class=argparse.RawDescriptionHelpFormatter)
#     path_help = str('The image to detect, can be web URI, '
#                     'Google Cloud Storage, or path to local file.')
#     parser.add_argument('image_url', help=path_help)
#     args = parser.parse_args()
report(annotate("http://www.photos-public-domain.com/wp-content/uploads/2011/01/old-vw-bug-and-van.jpg"))
    # [END vision_web_detection_tutorial_run_application]
# [END vision_web_detection_tutorial]
