from playwright.sync_api import sync_playwright
import traceback
import time
import requests
import numpy as np
from math import sqrt
import json
import csv
import unicodedata
import re
from scipy.optimize import least_squares
from random import *

game, id, town = "Villes-de-France", 39, "fr"
#game, id, town = "Villes-d-Europe", 44, "europa"

def trilateration(points, distances):
	points = np.array(points)
	distances = np.array(distances)

	def residuals(P):
		return np.linalg.norm(points - P, axis=1) - distances

	P0 = points.mean(axis=0)
	result = least_squares(residuals, P0)
	return result.x

def remove_accents(text):
	return "".join(
		c for c in unicodedata.normalize("NFD", text)
		if unicodedata.category(c) != "Mn"
	)

data = {}

# with open("cities500.txt", encoding="utf-8") as f:
# 	reader = csv.reader(f, delimiter="\t")
# 	for row in reader:
# 		city = row[1].lower()
# 		country = row[8]
# 		lat = float(row[4])
# 		lon = float(row[5])

# 		if country == "FR":
# 			data[remove_accents(city)] = [lon, lat]

# with open("cities.json", "w", encoding="utf-8") as f:
# 	json.dump(data, f, ensure_ascii=False, indent=4)

# citie_names = [
# 	"Bray-Dunes",
# 	"Brest",
# 	"Hendaye",
# 	"Menton",
# 	"Lauterbourg"
# ]

# cities = {}
# for c in citie_names:
# 	time.sleep(1)
# 	cities[c] = data[remove_accents(c).lower()]

cities = {
	'Bray-Dunes': [2.544968, 51.087423],
	'Brest': [-4.538493, 48.253468],
	'Hendaye': [-1.785498, 43.372465],
	'Menton': [7.529690, 43.784330],
	'Lauterbourg': [8.222403, 48.968649]
}

print(cities)

text_pos = []
positions = {}

def noised(target):
    if random() < 0.2:
        print("Changement")
        target = choice(list(data.keys()))

    print("pause")
    time.sleep(uniform(0.3, 0.6))
    print("play")
    x, y = play(target)

    if random() < 0.6:
        print("Moins precis")
        x *= uniform(0.95, 1.05)
    if random() < 0.6:
        y *= uniform(0.95, 1.05)
    print("click")
    return (x, y)


def play(target):
	pos_x = np.array([i[0] for i in positions.values()])
	pos_y = np.array([i[1] for i in positions.values()])
	cities_x = np.array([i[0] for i in cities.values()])
	cities_y = np.array([i[1] for i in cities.values()])

	default = list(data.keys())[0]
	target_x, target_y = data.get(target, data[default])

	target_x = (target_x - cities_x.min()) / (cities_x.max() - cities_x.min())
	target_y = (target_y - cities_y.min()) / (cities_y.max() - cities_y.min())

	target_x = target_x * (pos_x.max() - pos_x.min()) + pos_x.min()
	target_y = target_y * (pos_y.max() - pos_y.min()) + pos_y.min()

	d = []
	for (k1, v1), (k2, v2) in zip(positions.items(), cities.items()):
		x2, y2 = v2

		x2 = (x2 - cities_x.min()) / (cities_x.max() - cities_x.min())
		y2 = (y2 - cities_y.min()) / (cities_y.max() - cities_y.min())

		x2 = x2 * (pos_x.max() - pos_x.min()) + pos_x.min()
		y2 = y2 * (pos_y.max() - pos_y.min()) + pos_y.min()

		dx = abs(x2 - target_x)
		dy = abs(y2 - target_y)
		d.append(sqrt(dx**2 + dy**2))

	return trilateration(list(positions.values()), d)

data = {}

def extract_cities(js):
	pattern = re.compile(
		r'name\s*:\s*"([^"]+)"\s*,\s*la\s*:\s*([-\d.]+)\s*,\s*lo\s*:\s*([-\d.]+)'
	)
	results = []
	for line in js.split(";"):
		m = pattern.search(line)
		if m:
			data[remove_accents(m.group(1)).lower()] = [
				float(m.group(3)),
				float(m.group(2))
			]

def on_response(response):
	url = response.url
	if url.endswith(".js"):
		print(url.split("/")[-1])
		try:
			if f"towns_{town}" in url.split("/")[-1]:
				body = response.body().decode("utf-8", errors="ignore")
				extract_cities(body)
		except Exception as e:
			print("Erreur :", url, e)

diffs = {}

with sync_playwright() as p:
	try:
		browser = p.chromium.launch(headless=False)
		headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
		}
		page = browser.new_page()
		page.set_extra_http_headers(headers)

		page.on("response", on_response)
		reponse = page.goto(f"https://www.jeux-geographiques.com/jeux-en-ligne-{game}-_pageid{id}.html")
		page.wait_for_load_state("networkidle")

		time.sleep(0.5)
		page.click(".css-k8o10q")
		time.sleep(2)

		page.evaluate("""
		() => {
			const overlay = document.querySelector(".popup_overlay");
			if (overlay) overlay.style.pointerEvents = "none";
		}
		""")

		element = page.query_selector("i.btn_close")
		if element:
			element.click()
			time.sleep(0.5)

		page.click("#btn_fullscreen")

		page.evaluate(f"""
		() => {{
			window.__mousePos = {{ x: null, y: null }};
			window.__spacePositions = [];

			document.addEventListener("mousemove", (e) => {{
				window.__mousePos = {{
					x: e.clientX,
					y: e.clientY
				}};
			}});

			document.addEventListener("keydown", (e) => {{
				if (e.code === "Space") {{
					if (window.__mousePos.x !== null && window.__spacePositions.length < {len(cities)}) {{
						window.__spacePositions.push([
							window.__mousePos.x,
							window.__mousePos.y
						]);
					}}
				}}
			}});
		}}
		""")

		page.wait_for_function(f"window.__spacePositions.length === {len(cities)}")

		pos = page.evaluate("window.__spacePositions")
		for p, c in zip(pos, cities):
			positions[remove_accents(c).lower()] = p

		page.click("#buttonStart")
		time.sleep(1)

		previous_text = None
		count = 0
		total = None

		while not total:
			raw = page.locator("span#questionIndexLabel").text_content()
			if raw != "":
				total = int(raw.split("/")[1])

		while count <= total:
			text = page.locator("#questionTextLabel").text_content().strip().lower()

			if text != previous_text:
				time.sleep(0.1)
				previous_text = text
				#click_pos = play(remove_accents(text))
				click_pos = noised(remove_accents(text))
				page.mouse.click(*click_pos)
				count += 1

			dist_el = page.query_selector(".distanceLabel")
			if dist_el:
				dist = dist_el.text_content().split(" ")[0]
				diffs[tuple(click_pos)] = (dist, text)

		input("quitter")

	except Exception as inner_exception:
		print("Une erreur est survenue lors de l'ouverture de la page :", inner_exception)
		traceback.print_exc()

	browser.close()

print(diffs)
