#!/usr/bin/python

import sys, urllib, urllib2, poster, StringIO, datetime, os, getpass
from HTMLParser import HTMLParser

project = "moves2heia"
version = "1.03"

class Move:
	class Type:
		RUNNING = 1
		CYCLING = 2
		SWIMMING = 3
	def __init__(self):
		self.act_type = -1
		self.date = datetime.date(1984, 6, 28)
		self.path = ""
		self.duration = ""
		self.bpm = -1
		self.len = -1
		self.speed = ""
		self.pace = ""
		self.gpx = ""

	def get_hh_sport(self):
		"Returns heiaheia sport number"
		if self.act_type == Move.Type.RUNNING:
			return 1
		elif self.act_type == Move.Type.CYCLING:
			return 2
		elif self.act_type == Move.Type.SWIMMING:
			return 13
		else:
			return 14 # Default to walking

	def get_sport_str(self):
		"Returns the sport type in string"
		if self.act_type == Move.Type.RUNNING:
			return "running"
		elif self.act_type == Move.Type.CYCLING:
			return "cycling"
		elif self.act_type == Move.Type.SWIMMING:
			return "swimming"
		else:
			return "walking" # Default to walking

	def __repr__(self):
		return "Date: %s, path: %s, dur: %s, bpm: %d, len: %.2f, speed: %s" % (self.date.strftime("%d.%m.%Y"), self.path, self.duration, self.bpm, self.len, self.speed)

	def __str__(self):
		return "%10s %8s %10s %4d %6.2f %7s" % (self.date.strftime("%d.%m.%Y"), self.get_sport_str(), self.duration, self.bpm, self.len, self.pace)

def mc_authenticate(username, password):
	# Authenticate. Returns the cookies

	scoreboard_site = "http://www.movescount.com/fi/scoreboard/"
	login_site = "https://servicegate.suunto.com/UserAuthorityService/"
	data = {}
	data["emailAddress"] = username
	data["password"] = password
	data["service"] = "Movescount"
	data["_"] = "1398954112989"
	data["callback"] = "jQuery19101866209342144649_1398954112988"

	url_values = urllib.urlencode(data)

	headers = {}
	headers["Accept"] = "*/*"
	headers["Accept-Language"] = "en-US,en;q=0.5"
	headers["Connection"] = "keep-alive"
	headers["Host"] = "servicegate.suunto.com"
	headers["Referer"] = "http://movescount.com/fi/"
	headers["User-Agent"] = "User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:29.0) Gecko/20100101 Firefox/29.0"

	resp = urllib2.urlopen(login_site + "?" + url_values)

	content_len = resp.info().getheader('content-length')
	token = resp.read().split('"')[1]

	# Get cookie

	headers = {}
	headers["Host"] = "www.movescount.com"
	headers["User-Agent"] = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:29.0) Gecko/20100101 Firefox/29.0"
	headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
	headers["Accept-Language"] = "en-US,en;q=0.5"
	headers["Content-Type"] = "application/json; charset=utf-8"
	headers["X-Requested-With"] = "XMLHttpRequest"
	headers["Referer"] = "http://www.movescount.com/fi/"
	headers["Content-Length"] = "97"
	headers["Connection"] = "keep-alive"
	headers["Pragma"] = "no-cache"
	headers["Cache-Control"] = "no-cache"

	data = """{"token":"%s","utcOffset":"180","redirectUri":"/fi/scoreboard"}""" % token

	req = urllib2.Request("http://www.movescount.com/fi/services/UserAuthenticated", headers = headers)
	resp = urllib2.urlopen(req, data = data)
	cookies = []
	for entry in resp.info().getallmatchingheaders("Set-Cookie"):
		if "path=/; HttpOnly; path=/" in entry:
			continue
		cookies.append(entry.split("Set-Cookie: ")[1].split(";")[0])
	return cookies

def get_scoreboard(cookies):
	# Get scoreboard. Returns the scoreboard as a list of Move objects

	headers = {}
	headers["Host"] = "www.movescount.com"
	headers["User-Agent"] = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:29.0) Gecko/20100101 Firefox/29.0"
	headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
	headers["Accept-Language"] = "en-US,en;q=0.5"
	headers["Referer"] = "http://www.movescount.com/fi/"
	headers["Cookie"] = "; ".join(cookies) + "; Movescount_lang=9"
	headers["Connection"] = "keep-alive"

	req = urllib2.Request("http://www.movescount.com/fi/scoreboard", headers = headers)
	page = urllib2.urlopen(req).read()

	moves = []
	m = False
	class MyHTMLParser(HTMLParser):
		in_table = False
		ul_cnt = 0
		def handle_starttag(self, tag, attrs):
			if tag == "ul" and "id" in [entry[0] for entry in attrs] and "LatestMovesTable" in [entry[1] for entry in attrs]:
				#print "Encountered a start tag:", tag, attrs
				self.in_table = True
			elif self.in_table and tag == "ul":
				self.ul_cnt += 1
			elif self.in_table and tag == "a" and "href" in [entry[0] for entry in attrs]:
				#<a href="/fi/moves/move30713215" target="_self">
				for entry in attrs:
					if "href" in entry[0]:
						moves[-1].path = entry[1]
			elif self.in_table and "title" in [entry[0] for entry in attrs]:
				for entry in attrs:
					if "title" in entry[0]:
						moves.append(Move())
						sprt = entry[1].lower()
						if ("running" == sprt or "juoksu" == sprt):
							moves[-1].act_type = Move.Type.RUNNING
						elif ("cycling" == sprt or "py" == sprt[:2]):
							moves[-1].act_type = Move.Type.CYCLING
						elif ("swimming" == sprt or "uinti" == sprt):
							moves[-1].act_type = Move.Type.SWIMMING
						else:
							print "Unknown sport encountered: " + entry[1]
		def handle_endtag(self, tag):
			if tag == "ul" and self.in_table and self.ul_cnt == 0:
				self.in_table = False
				#print "Encountered an end tag :", tag
			elif tag == "ul" and self.in_table:
				self.ul_cnt -= 1
		def handle_data(self, data):
			data = data.strip()
			if self.in_table and self.ul_cnt == 1 and len(data) != 0:
				#print "Encountered some data  :", data
				if len(data.split(".")) == 3:
					moves[-1].date = datetime.date(int(data.split(".")[2]), int(data.split(".")[1]), int(data.split(".")[0]))
				elif "tuntia" in data or "hours" in data:
					moves[-1].duration = data.split(" ")[0]
				elif "bpm" in data:
					moves[-1].bpm = int(data.split(" ")[0])
				elif "km" in data and "km/h" not in data:
					moves[-1].len = float(data.split(" ")[0].replace(",", "."))
				elif "km/h" in data:
					km_speed = float(data.split(" ")[0].replace(",", "."))
					min_speed = 1.0 / (km_speed / 60.0) if km_speed != 0.0 else 0.0
					moves[-1].speed = km_speed
					moves[-1].pace = str(int(min_speed)) + "'" + str(int((min_speed % 1.0) * 60.0))
			
	parser = MyHTMLParser()
	parser.feed(page)

	return moves

def print_moves(moves):
	print "         Date    Sport   Duration  bpm     km  min/km"
	for i, move in enumerate(moves):
		print "%d. %s" % (i+1, str(move))
	print ""

def hh_authenticate(username, password):
	# Authenticate. Returns the cookies

	cookie = None
	resp = urllib2.urlopen("https://www.heiaheia.com/account")
	for entry in resp.info().getallmatchingheaders("Set-Cookie"):
		cookie = entry.split("Set-Cookie: ")[1].split(";")[0]
		
	if not cookie:
		raise Exception("Unable to get cookie from the server")

	headers = {}
	headers["Cookie"] = cookie
	req = urllib2.Request("https://www.heiaheia.com/login", headers = headers)
	page = urllib2.urlopen(req).read()

	class MyHTMLParser(HTMLParser):
		token = None
		def handle_starttag(self, tag, attrs):
			if tag == "meta" and "content" in [entry[0] for entry in attrs] and "csrf-token" in [entry[1] for entry in attrs]:
				self.token = attrs[0][1]
	
	parser = MyHTMLParser()
	parser.feed(page)

	token = parser.token
	if not token:
		raise Exception("Unable to get authenticity token from login page")

	# Get cookie
	headers = {}
	headers["Host"] = "www.heiaheia.com"
	headers["User-Agent"] = "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:30.0) Gecko/20100101 Firefox/30.0"
	headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
	headers["Accept-Language"] = "en-US,en;q=0.5"
	headers["Referer"] = "https://www.heiaheia.com/login"
	headers["Connection"] = "keep-alive"
	headers["Cookie"] = cookie

	data = {}
	data["authenticity_token"] = token
	data["commit"] = "Sign In"
	data["user"] = {}
	data["user"]["email"] = {username}
	data["user"]["password"] = {password}
	q_token = urllib.quote_plus(token)
	username = urllib.quote_plus(username)
	password = urllib.quote_plus(password)

	data = "authenticity_token=" + q_token + "&commit=Sign%20In&user%5Bemail%5D=" + username +"&user%5Bpassword%5D=" + password + "&utf8=%E2%9C%93"
	req = urllib2.Request("https://www.heiaheia.com/account/authenticate?%s" % data, headers = headers)
	resp = urllib2.urlopen(req, "")

	# Put cookie data into a dictionary
	cookie_dict = {}
	for entry in cookie.split("; "):
		cookie_dict[entry.split("=")[0].strip()] = entry.split("=")[1].strip()

	# Get new cookie
	cookie = None
	for entry in resp.info().getallmatchingheaders("Set-Cookie"):
		cookie = entry.split("Set-Cookie: ")[1].split(";")[0]
	if not cookie:
		raise Exception("Unable to get cookie from the server")

	
	# Append the new cookie data to the existing
	for entry in cookie.split("; "):
		cookie_dict[entry.split("=")[0].strip()] = entry.split("=")[1].strip()
		
	return (token, cookie_dict)

def hh_post_training(token, cookie, move, comment):
	# This function posts a move to heiaheia

	# Stringify the cookie
	cookie_str = ""
	for key in cookie.keys()[:-1]:
		cookie_str += key + "=" + cookie[key] + ", "
	cookie_str += cookie.keys()[-1] + "=" + cookie[cookie.keys()[-1]]

	headers = {}
	headers["Host"] = "www.heiaheia.com"
	headers["User-Agent"] = "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:30.0) Gecko/20100101 Firefox/30.0"
	headers["Accept-Language"] = "en-US,en;q=0.5"
	headers["Referer"] = "https://www.heiaheia.com/login"
	headers["Connection"] = "keep-alive"
	headers["Cookie"] = cookie_str

	gpx = StringIO.StringIO(move.gpx)
	poster.streaminghttp.register_openers()

	gpx = poster.encode.MultipartParam("training_log[tracks_attributes][][file_gpx]", filename="move.gpx", fileobj=gpx, filetype="application/octet-stream")

	params = [ \
	("utf8" , u"\u2713"),
	("authenticity_token" , token),
	("training_log[sport]" , str(move.get_hh_sport())),
	("training_log[date]" , move.date.strftime("%d.%m.%Y")),
	("training_log[duration_h]" , move.duration.split(":")[0]),
	("training_log[duration_m]" , move.duration.split(":")[1].split("'")[0]),
	("training_log[duration_s]" , move.duration.split("'")[1].split(".")[0]),
	("training_log[distance]" , "%.2f" % move.len),
	("training_log[comment]" , comment),
	("training_log[mood]" , "0"),
	("trining_log[tags_attributes][]" , ""),
	("training_log[private]" , "0"),
	("training_log[exclude_stats]" , "0"),
	("training_log[calories]" , ""),
	("training_log[avg_hr]" , "%d" % move.bpm),
	("training_log[max_hr]" , ""),
	gpx,
	("training_log[favourite]" , "false"),
	("button", "")
	]
	datagen, post_headers = poster.encode.multipart_encode(params)

	headers = dict(headers.items() + post_headers.items())

	"""string = ""
	for s in datagen:
		string += s
	gpx_lines = []
	for s in string.split("\r\n"):
		if "<" in s and ">" in s:
			gpx_lines.append(s[:60])
		else:
			if len(gpx_lines) > 20:
				print "\n".join(gpx_lines[:10])
				print "..."
				print "\n".join(gpx_lines[-10:])
			elif len(gpx_lines) != 0:
				print "\n".join(gpx_lines)
			gpx_lines = []
				
			print s"""

	request = urllib2.Request('https://www.heiaheia.com/training_logs.js', datagen, headers)
	urllib2.urlopen(request)

def get_gpx(cookies, move):
	headers = {}
	headers["Host"] = "www.movescount.com"
	headers["User-Agent"] = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:29.0) Gecko/20100101 Firefox/29.0"
	headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
	headers["Accept-Language"] = "en-US,en;q=0.5"
	headers["Cookie"] = "; ".join(cookies) + "; Movescount_lang=9"
	headers["Connection"] = "keep-alive"
	headers["Referer"] = "http://www.movescount.com/" + move.path

	req = urllib2.Request("http://www.movescount.com/fi/move/export?id=%s&format=gpx" % move.path.split("moves/move")[1], headers = headers)
	gpx = urllib2.urlopen(req).read()

	move.gpx = gpx

def get_cookies():
	# Reads cookies from local file
	dr = ""
	if "win" in sys.platform:
		# Windows
		dr = os.path.join(os.getenv('APPDATA'), "moves2heia")
	else:
		dr = os.path.join(os.path.expanduser("~"), ".moves2heia")

	f = open(os.path.join(dr, "cookies"), "r")

	mc_cookies = f.readline().strip().split("; ")
	hh_cookie_str = f.readline().strip()
	hh_token = f.readline().strip()

	hh_cookie = {}
	for entry in hh_cookie_str.split(", "):
		hh_cookie[entry.split("=")[0]] = entry.split("=")[1]

	return (mc_cookies, hh_cookie, hh_token)

def store_cookies(mc_cookies, hh_cookie, hh_token):
	# Stores cookies into a local file

	dr = ""
	if "win" in sys.platform:
		# Windows
		dr = os.path.join(os.getenv('APPDATA'), "moves2heia")
	else:
		dr = os.path.join(os.path.expanduser("~"), ".moves2heia")

	try:
		os.makedirs(dr)
	except:
		pass

	hh_cookie_str = ""
	for key in hh_cookie.keys()[:-1]:
		hh_cookie_str += key + "=" + hh_cookie[key] + ", "
	hh_cookie_str += hh_cookie.keys()[-1] + "=" + hh_cookie[hh_cookie.keys()[-1]]
	
	f = open(os.path.join(dr, "cookies"), "w")
	f.write("; ".join(mc_cookies) + "\n")
	f.write(hh_cookie_str + "\n")
	f.write(hh_token + "\n")

def uname_auth():
	# Authenticates to movescount and heiaheia with username + password
	movescount_uname = None
	movescount_pw = None
	heiaheia_uname = None
	heiaheia_pw = None

	if len(sys.argv) > 1:
		movescount_uname = sys.argv[1]
	if len(sys.argv) > 2:
		movescount_pw = sys.argv[2]
	if len(sys.argv) > 3:
		heiaheia_uname = sys.argv[3]
	if len(sys.argv) > 4:
		heiaheia_pw = sys.argv[4]

	if not movescount_uname:
		movescount_uname = raw_input("Movescount username: ")
	if not movescount_pw:
		movescount_pw = getpass.getpass("Movescount password: ")
	if not heiaheia_uname:
		heiaheia_uname = raw_input("Heiaheia username: ")
	if not heiaheia_pw:
		heiaheia_pw = getpass.getpass("Heiaheia password: ")

	mc_cookies = mc_authenticate(movescount_uname, movescount_pw)
	print "Movescount authenticated"
	hh_token, hh_cookie = hh_authenticate(heiaheia_uname, heiaheia_pw)
	print "Heiaheia authenticated"

	return (mc_cookies, hh_cookie, hh_token)

def main():

	cookies_read = False
	cookies_used = False

	print "%s version %s starting.." % (project, version)
	print "Cancel at any time by pressing CTRL+C"

	if len(sys.argv) == 2 and sys.argv[1] == "-h":
		print "Usage: %s [movescount_uname [movescount_pw [heiaheia_uname [heiaheia_pw]]]][-c (cookie auth)]" % sys.argv[0]
		sys.exit(0)

	try:
		mc_cookies, hh_cookie, hh_token = get_cookies()
		cookies_read = True
	except:
		pass

	if cookies_read:
		use_cookies = raw_input("Cookies available on filesystem, use them and skip password authentication? (Cookies get obsolete at some point) [Y/n]: ")
		if use_cookies.strip().upper() == "N":
			mc_cookies, hh_cookie, hh_token = uname_auth()
		else:
			cookies_used = True
	else:
		mc_cookies, hh_cookie, hh_token = uname_auth()

	moves = get_scoreboard(mc_cookies)
	print "Scoreboard fetched"
	print_moves(moves)

	moveno = int(raw_input("Which move to post:\n")) -1
	move = moves[moveno]
	get_gpx(mc_cookies, move)
	print "GPX fetched"

	comment = raw_input("A comment for your training:\n").decode(sys.stdin.encoding)

	hh_post_training(hh_token, hh_cookie, move, comment)
	print "Training posted"

	if not cookies_used:
		store_cookie = raw_input("Store the cookies to skip passwords next time (stored in clear text)? [Y/n]: ")
		if store_cookie.strip().upper() != "N":
			store_cookies(mc_cookies, hh_cookie, hh_token)

main()
