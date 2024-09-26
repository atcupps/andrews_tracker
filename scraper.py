from bs4 import BeautifulSoup
import os
import requests
from supabase import create_client, Client

# Data used in this script
url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_KEY']
term = '202501'

# Supabase client
supabase: Client = create_client(url, key)
print('Created Supabase client.')

# Download course code list file from Supabase and save locally
bucket_name = 'class_list'
file_path = 'courses_list.txt'

print('Sending request to GitHub for course list file download.')
course_list = requests.get("https://raw.githubusercontent.com/atcupps/Jupiterp/main/datagen/data/courses_list.txt").text
print('Courses downloaded successfully.')

# Split response into chunks, send request to Testudo, and collect section
# seat information in a dictionary with the following form:
# { (course_code, section_code) : (current_seats, total_seats) }
course_codes = course_list.split('\n')[0:-1]
length = len(course_codes)
chunk_size = int(length / 10)
l = 0
r = chunk_size
seat_info = dict()
while l < length:
    codes_for_url = course_codes[l:r]

    print(f'Getting Testudo sections page for {len(codes_for_url)} courses: {codes_for_url[0]} to {codes_for_url[-1]}')
    testudo_url = f'https://app.testudo.umd.edu/soc/{term}/sections?courseIds=' + ','.join(codes_for_url)
    response = requests.get(testudo_url)
    print('Testudo page successfully retreived. Beginning parsing')
    html = response.text
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
supabase.table('seats').insert(full_data).execute()