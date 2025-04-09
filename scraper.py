from bs4 import BeautifulSoup
import os
import requests
from supabase import create_client, Client
from handler import Handler
import time

# Data used in this script
url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_KEY']
term = '202508'

# Error handling
err_handler = Handler()

# Supabase client
try:
    supabase: Client = create_client(url, key)
    print('Successfully created Supabase client.')
except Exception as e:
    print('Failed to create Supabase client.')
    err_handler.error_supabase(e)
    err_handler.send_email()
    exit(1)

# Download course code list file from Supabase and save locally
bucket_name = 'class_list'
file_path = 'courses_list.txt'

'''
Try `num_attempts` times to send a request; returns response text if
successful, or `None` if the response failed. Assumes `num_attempts > 0`.
'''
def attempt_request(url, num_attempts):
    print(f'Attempting request: {num_attempts} remaining attempts')
    response = requests.get(url)
    if response.ok:
        return response.text
    else:
        if num_attempts - 1 > 0:
            return attempt_request(url, num_attempts - 1)
        else:
            print('Failed to get valid response for request.')
            return None

'''
Get list of courses from Jupiterp GitHub. Returns courses as an array of strings.
'''
def retrieve_all_courses(attempts):
    print(f'Sending request to GitHub for course list file download.')
    request = 'https://raw.githubusercontent.com/atcupps/Jupiterp/main/datagen/data/courses_list.txt'
    response_text = attempt_request(request, attempts)
    if response_text == None:
        print('Failed to get courses.')
        err_handler.error_request_failed(request)
        return None
    else:
        course_list = response_text.split('\n')[0:-1]
        print(f'Successfully retrieved {len(course_list)} courses.')
        return course_list

'''
Get Testudo SOC page for a list of courses.
'''
def retrieve_testudo_page(courses, attempts):
    print(f'Sending request to Testudo Schedule of Classes.')
    testudo_url = f'https://app.testudo.umd.edu/soc/{term}/sections?courseIds=' + ','.join(courses)
    response_text = attempt_request(testudo_url, attempts)
    if response_text == None:
        print(f'Failed to get Testudo page for URL: {testudo_url}')
        err_handler.error_request_failed(testudo_url)
        return None
    else:
        print('Successfully retrieved Testudo SOC page.')
        return response_text

# Split response into chunks, send request to Testudo, and collect section
# seat information in a dictionary with the following form:
# { (course_code, section_code) : (current_seats, total_seats) }
course_codes = retrieve_all_courses(3)
if course_codes == None:
    print('Failed to retrieve courses.')
    err_handler.send_email()
    exit(1)

length = len(course_codes)
chunk_size = int(length / 50)
l = 0
r = chunk_size
seat_info = dict()
while l < length:
    # Wait 1 second so I don't get in trouble for spamming Testudo
    time.sleep(1)

    # Get Testudo SOC page for this chunk of courses
    codes_for_url = course_codes[l:r]
    html = retrieve_testudo_page(codes_for_url, 3)

    if html != None:
        print('Testudo page successfully retreived. Beginning parsing')
        soup = BeautifulSoup(html, 'html.parser')
        
        for course_id in codes_for_url:
            print(f'Parsing seats info for: {course_id}'.ljust(40), end='\r')
            course_div = soup.find('div', id=course_id)

            if course_div != None:
                sections = course_div.find_all('div', class_='section')

                for section in sections:
                    section_id = section.find('input', {'name' : 'sectionId'})['value']
                    open_seats = int(section.find('span', class_='open-seats-count').get_text())
                    total_seats = int(section.find('span', class_='total-seats-count').get_text())
                    waitlist = int(section.find('span', class_='waitlist-count').get_text())
                    seat_info[(course_id, section_id)] = (open_seats, total_seats, waitlist)
    else:
        print(f'Failed to get page for {len(codes_for_url)} courses')

    l = r
    r = min(r + chunk_size, length)

# Upload data to Supabase. To avoid the presence of outdated data within the
# seats database, this script deletes all rows then rewrites them with the
# data from this script.
print('Deleting all rows from table `seats`.')
supabase.table('seats').delete().neq('course_id', 0).execute()
print('Rows deleted.')

print('Creating bulk data array for upload to database.')
full_data = []
for (course, section) in seat_info:
    (current, max, waitlist) = seat_info[(course, section)]
    full_data.append({
        'course_id': course,
        'section_id': section,
        'current_seats': current,
        'max_seats': max,
        'waitlist': waitlist
    })

print('Uploading all data to database.')
try:
    supabase.table('seats').insert(full_data).execute()
except Exception as e:
    print('Failed to upload to database.')
    err_handler.error_supabase(e)

err_handler.send_email()