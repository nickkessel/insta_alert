import requests
from bs4 import BeautifulSoup
import re

def get_watch_number(desc):
    """Generates the watch number/id from product text

    Args:
        desc (str): alert description text content

    Returns:
        watch_id: Watch ID number in format (####) where the number is on the right, padded left as needed by zeroes.
    """    
    watch_id_match = re.search(r'\b\d{1,4}\b', desc) #get the first instance of any 1 to 4 digit number in the watch desc (the watch number)
    if watch_id_match:
        watch_id = watch_id_match.group(0)
        return watch_id
    else:
        print(f'error getting watch id from description! desc text: {desc}')
        return None

blank_watch_url = 'https://www.spc.noaa.gov/products/watch/ww' #+ XXXX.html
def get_watch_attributes(id):
    '''
    Given a watch id, scrapes the SPC website to get the watch attributes (probabilities for severe hazards)
    Args: 
        id (int): The SPC ID (#XXXX) of the watch.
        
    Returns:
        has_attribs (bool): indicating if the watch has attributes (ie can be plotted)
        List of watch attribute verbs
        List of watch attribute percentages
    '''
    id = str(id).zfill(4) #pads the left side w/ 0s until its 4 wide (proper format for the spc website)
    target_watch_url = f'{blank_watch_url}{id}.html'
    print(f"Target URL: {target_watch_url}")
    
    try:
        response = requests.get(target_watch_url)
        html_content = response.content
        soup = BeautifulSoup(html_content, 'lxml') #want to get the first 6 things with class="wblack", which is the name of the class in the site that has the watch percentages.
        attribs = soup.find_all(class_='wblack')
        attribs = attribs[:6] #first 6, gets repeitive after that for the like different views
        watch_attribs = [tag.text for tag in attribs] #get only the text content
        percents = [tag['title'].replace('% probability', '\%') for tag in attribs] 
        print(watch_attribs, percents)
        return True, watch_attribs, percents
    except Exception as e:
        print(f'error getting watch attributes: [{e}]')
        return False, ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a'], ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a']
