import urllib.request
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import threading
from random import randint
from time import sleep
import os

import boto
import boto3

# Elastic Search
import requests
from requests_aws4auth import AWS4Auth
from elasticsearch import Elasticsearch
es=Elasticsearch(hosts='https://search-cap-resume-es-fu3rqbrrqvbmeql5pfeal4nx3m.us-east-1.es.amazonaws.com')

region='us-east-1'
service='es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)


class Resume(object):

	def __init__ (self, idd, jobs, schools, skills, add_info):
		self.id = idd
		self.jobs = jobs
		self.schools = schools
		self.skills = skills
		self.add_info = add_info

	def toJSON(self):
		return json.dumps(self, default=lambda o: o.__dict__, 
			sort_keys=True, indent=0)


class Job(object):
	def __init__(self, title, company, location, hire_date):
		self.title = title
		self.company = company
		self.location = location
		self.hire_date = hire_date

class School(object):
	def __init__(self, degree, school_name, grad_date):
		self.degree = degree
		self.school_name = school_name
		self.grad_date = grad_date

class Skill(object):
	def __init__(self, skill, years):
		self.skill=skill
		self.years=years
	



def gen_idds(url, driver):
	driver.get(url)
	time.sleep(5)
	p_element = driver.page_source
	time.sleep(4)
	soup = BeautifulSoup(p_element, 'html.parser')
	links = soup.find_all(class_="icl-TextLink icl-TextLink--primary rezemp-u-h4")

	idds=[]

	for link in links:
		path = link.get("href")
		#print(path[8:path.find("?")]) #8 is to account for "\resume\" at the beginning
		idds.append(path[8:path.find("?")])

	return idds
#print(idds)

def gen_resume(idd, driver):
	URL = '''https://resumes.indeed.com/resume/''' + idd


	driver.get(URL)
	p_element = driver.page_source
	soup = BeautifulSoup(p_element, 'html.parser')

	results = soup.find_all('div', attrs={"class":"rezemp-ResumeDisplaySection"})
	#print(results)



	schools = []


	try:
		education = results[1]
		# print('EDUCATION\n', edudation, '\n')
		content = education.find(class_="rezemp-ResumeDisplaySection-content")
		for uni in content.children:
			degree = uni.find(class_ = "rezemp-ResumeDisplay-itemTitle").get_text()
			university = uni.find(class_="rezemp-ResumeDisplay-university").contents[0].get_text()
			date = uni.find(class_="rezemp-ResumeDisplay-date").get_text()
			schools.append(School(degree, university, date))
	except:
		print('end of education or could not retrive education')


	jobs = []


	try:
		work_experience = results[0]
		# print('WORK:\n', work_experience, '\n')
		job_titles = work_experience.find_all(class_="rezemp-u-h4")
		job_descriptions = work_experience.find_all(class_="rezemp-u-h5")
		for i in range(len(job_titles)):
			dates = job_descriptions[i].find_next_sibling().get_text()
			date = dates[:dates.find("to")]
			title = job_titles[i].get_text()
			desc = [p.get_text() for p in job_descriptions[i].find_all("span")][1:]
			company = desc[0]
			location = desc[1]
			jobs.append(Job(title, company, location, date))
	except:
		print('could not retrive work experiences')


	skills = []


	try:
		field = results[2]
		# print(results[2])
		content = field.get_text()
		# print(content)
		if content[:6]=='Skills':
			content = content[6:].split(',')
			for skl in content:
				slp = skl.split('(')  # slp = skill_length_pair
				skills.append(Skill(slp[0], slp[1]))


	except:
		print('could not retrive skills')


	add_info = []

	try:
		field = results[-1]
		# print(results[2])
		content = field.get_text()
		# print(content)
		if content[:22]=='Additional Information':
			add_info.append(content[22:])
			# content[22:].split('\n')
			# print(add_info)

	except:
		print('could not retrive additional Information')

	return Resume(idd, jobs, schools, skills, add_info)



def mine(name, URL, override=True, rangee=None):
	driver = webdriver.Chrome()
	# print('driver created\nNow waiting...')
	driver.implicitly_wait(10)
	# print('wait over')


	if(override):
		with open('resume_output_' + name + '.json', 'w') as outfile:
			outfile.write("")


	if rangee == None:	
		start_index = 0
		target = 1050
	else:
		start_index = rangee[0]
		target = rangee[1]


	print(start_index, target)

	while 1:
		if (start_index >= target):
			break
		
		stri = URL+"&start="+str(start_index)
		print(stri)
		# wait = WebDriverWait(driver, 20)
		# element = wait.until(EC.presence_of_all_elements_located())
		idds = gen_idds(URL+"&start="+str(start_index), driver)
		print(idds)
		if(len(idds) == 0):
			time.sleep(4)
			continue




		# for idd in idds:
		# 	with open('resume_output_' + name + '.json', 'a') as outfile:
		# 		resume = gen_resume(idd, driver)
		# 		json.dump(resume.toJSON(), outfile)
		# 		print(resume)
		# 		# print('waiting before the next resume...')
		# 		# time.sleep(100)

		for idd in idds:
			js = gen_resume(idd,driver).toJSON()
			print(js)
			es.index(index='id',body=js, doc_type='resume')

		start_index+=50

	# resumes = [gen_resume(idd).toJSON() for idd in idds] 

	driver.close()


def mine_multi(name, url, override=True):


	thread_list = []
	names = []

	target = 100
	tr = 4
	for i in range(tr):
		# Instantiates the thread
		# (i) does not make a sequence, so (i,)
		t = threading.Thread(target=mine, args=(name+str(i),url,), kwargs={"override" : override, "rangee" : (i*(target//tr), (i+1)*(target//tr)),})
		# Sticks the thread in a list so that it remains accessible
		thread_list.append(t)
		names.append("resume_output_" + name + str(i) +".json")
		time.sleep(3)

	# Starts threads
	for thread in thread_list:
		thread.start()

	# This blocks the calling thread until the thread whose join() method is called is terminated.
	# From http://docs.python.org/2/library/threading.html#thread-objects
	for thread in thread_list:
		thread.join()
		time.sleep(3)


	consolidate_files(name, names)


def consolidate_files(name, names):
	file = open("resume_output_" + name + ".json", "a")
	for nam in names:
		with open(nam, 'r') as read:
			file.write(read.read())
		os.remove(nam)
			
	file.close()



def main():



	t = time.clock()
	search_terms= input('Search terms: ')
	location= input('Location: ')
	fle = input('File Name: ')

	#idds = ["f845ad88e3d17704", "1992c61c49a470e1"]

	#URL = "https://resumes.indeed.com/search?l=california&q=software%20engineer&searchFields="

	# ---------------------------------------------------------------------------------------
	# URL = "https://resumes.indeed.com/search?q=data+scientist&l=new+york&searchFields="
	# mine("datascientist_newyork", URL)

	# URL = "https://resumes.indeed.com/search?q=data+scientist&l=north+carolina&searchFields="
	# mine("datascientist_nc", URL)

	# URL = "https://resumes.indeed.com/search?q=data+scientist&l=chicago&searchFields="
	# mine("datascientist_chicago", URL)

	URL = "https://resumes.indeed.com/search?q="+search_terms+"&l="+location+"&searchFields="
	mine_multi(fle, URL)

	# URL = "https://resumes.indeed.com/search?q=data+scientist&l=california&searchFields="
	# mine("datascientist_california", URL)
	# ---------------------------------------------------------------------------------------


	#mine("software_engineers_california", URL, override = False)


	#consolidate_files("lawyer-california", ["resume_output_lawyer-california" + str(i) +".json" for i in range(8)])

	# mine("test_data", URL)


	print(time.clock() - t),


main()