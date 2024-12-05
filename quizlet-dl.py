from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup

import time, sys, os, json, secrets

def scrollDown(driver: webdriver.Firefox): #Scroll to load all the sets within a user page
    last_height = driver.execute_script('return document.body.scrollHeight')
    while True:
        scrollTo = str(driver.execute_script('return document.body.scrollHeight')) #Scroll to the very bottom of the page
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1)
        new_height = driver.execute_script('return document.body.scrollHeight')

        if new_height == last_height: #If scrolling resulted in no change, return the function
            return
        last_height = new_height


def scrapeUser(driver: webdriver.Firefox): #Scrapes an entire user page
    sets_raw = []
    sets = []

    #Get number of sets within page via the Xpath
    
    numOfSets = driver.find_element(By.XPATH, '/html/body/div[3]/div[2]/div/div/section/div/div[1]/div/div/div/div/div[2]/div[2]/div/span[1]/span').text[9:-1]
    numOfSets = int(numOfSets)
    
    while len(sets) != numOfSets: #Keep discovering sets until the number of sets discovered equals the number of sets stated at the top of the user page
        for set_ in driver.find_elements(By.CLASS_NAME, 'DashboardListItem'):
            foo = set_.find_elements(By.CLASS_NAME, 'UILink')[0]
            if foo not in sets_raw:
                sets_raw.append(foo)
                sets.append(foo.get_attribute('href'))
        scrollDown(driver)

    for set_ in sets: #Scrape every set within the user page
        print(set_)
        driver.get(set_) #Load the set within the browser
        scrapeSet(driver)


def scrapeSet(driver: webdriver.Firefox): #Scrape a single set of cards
    #driver.execute_script('window.scrollTo(0, 400)') #Scroll to *almost* the bottom. Needed to load the "see more" button
    
    source = driver.page_source
    source = source[source.find('Terms in this set') + 19 : -1] #Manually find the # of cards within the set
    numOfCards = source[0:source.find(')')]                     #May be a better way to do this within Selenium, but the XPath appears
                                                                #to change for each set, so this will work for now.
    
    seeMore = driver.find_element(By.XPATH, "//span[text()='See more']")
    if seeMore: #If a "see more" button exists, click it
        print('I see the button')
        driver.execute_script("arguments[0].scrollIntoView(true);", seeMore)
        ActionChains(driver).move_to_element(seeMore).click().perform()

    #Add all terms and definitions to their corresponding list
    while True:
        try:
            terms, definitions = [], []
            for entries in driver.find_elements(By.CLASS_NAME, 'SetPageTerms-term'):
                spans = entries.find_elements(By.TAG_NAME, 'span')
                terms.append(spans[1].text)
                definitions.append(spans[3].text)
            break
        except:
            time.sleep(0.25)
    if len(terms) != len(definitions):
            print('ERROR: Number of terms does not match number of definitions.')
            print('ERROR: Number of terms does not match to number of total cards.')
            return None

    cards = []
    for i in range(0,len(terms)):
        cards.append({terms[i]:definitions[i]})

    saveCards(terms, definitions, driver)

def saveCards(terms, definitions, driver: webdriver.Firefox):
    try:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        title = soup.find('h1').text
    except:
        title = f"{secrets.token_hex(16)}" #Fallback
    user = driver.find_element(By.CLASS_NAME, 'UserLink-username').text
    id_ = driver.current_url.split('/')[-3]

    invalid_chars = ['/','\\',':','?','\"','<','>','|']
    for i in invalid_chars:
        title = title.replace(i, '')
        user = user.replace(i, '')

    data = [] #Data to be output in JSON
    data.append({'title':title})

    cards = []
    for i in range(0,len(terms)):
        cards.append({terms[i]:definitions[i]})
    data.append({'cards':cards})

    basedir = sys.argv[2].replace('\\', '/')
    if basedir[-1] == '/':
        basedir = basedir[0:-1]
    jsondir = '{}/{}/'.format(basedir, user)

    try:
        os.mkdir(jsondir)
    except FileExistsError:
        pass
    except PermissionError:
        print('Permission denied - try running as an administrator')
        input('Press enter to exit...')
        sys.exit()
    except FileNotFoundError:
        print('Error: Make sure your directory is correct and you are specifying the full path.')
        input('Press enter to exit...')
        sys.exit()

    with open(jsondir+title+' - '+id_+'.json', 'w+') as fp:
        json.dump(data, fp, sort_keys=True, indent=4)
    
def main():
    try:
        opts = Options()
        opts.add_argument("--headless")
        driver = webdriver.Firefox(options=opts)

        driver.get(sys.argv[1])
        if driver.find_elements(By.CLASS_NAME, 'ProfileHeader-user'):
            scrapeUser(driver)
        else:
            scrapeSet(driver)
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
