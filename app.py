from flask import Flask, render_template, request, jsonify
from queue import PriorityQueue
import math
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# ─── Email Config ─────────────────────────────────────────────────────────────
SMTP_SERVER    = "smtp.gmail.com"
SMTP_PORT      = 465
SENDER_EMAIL   = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD= os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

# ─── Campus Locations (Real KIIT Coordinates) ─────────────────────────────────
LOCATIONS = {
    "Campus 3":                      {"lat": 20.3531, "lng": 85.8165},
    "Campus 6":                      {"lat": 20.3525, "lng": 85.8195},
    "Campus 8":                      {"lat": 20.3512, "lng": 85.8194},
    "Campus 12":                     {"lat": 20.3545, "lng": 85.8194},
    "Campus 13":                     {"lat": 20.3565, "lng": 85.8185},
    "Campus 14":                     {"lat": 20.3561, "lng": 85.8154},
    "Campus 15":                     {"lat": 20.3487, "lng": 85.8148},
    "Campus 17":                     {"lat": 20.3492, "lng": 85.8194},
    "Campus 20":                     {"lat": 20.3540, "lng": 85.8162},
    "Campus 25":                     {"lat": 20.3640, "lng": 85.8162},
}

# ─── Campus Graph (Adjacency List, weights in km) ─────────────────────────────
GRAPH = {
    "Campus 3":  [
        ("Campus 20", 0.059),
        ("Campus 14", 0.4),
        ("Campus 15", 0.5),
    ],
    "Campus 6": [
        ("Campus 3",  0.4),
        ("Campus 12", 0.16),
        ("Campus 8",  0.45),
    ],
    "Campus 8":  [
        ("Campus 6", 0.45),
        ("Campus 17", 0.26),
    ],
    "Campus 12": [
        ("Campus 6", 0.16),
        ("Campus 13", 0.3),
    ],
    "Campus 13": [
        ("Campus 12", 0.3),
        ("Campus 14", 0.4),
    ],
    "Campus 14": [
        ("Campus 13",  0.4),
        ("Campus 25",  1.2),
        ("Campus 20",  0.35),
    ],
    "Campus 15": [
        ("Campus 3",  0.5),
        ("Campus 17", 0.55),
    ],
    "Campus 17": [
        ("Campus 8",  0.26),
        ("Campus 15", 0.55),
    ],
    "Campus 20": [
        ("Campus 3",  0.059),
        ("Campus 14", 0.35),
    ],
    "Campus 25": [
        ("Campus 14", 1.2),
    ],
}

# ─── Heuristic (Euclidean distance in km) ─────────────────────────────────────
def heuristic(node1, node2):
    loc1, loc2 = LOCATIONS[node1], LOCATIONS[node2]
    lat_diff = (loc1["lat"] - loc2["lat"]) * 111000
    lng_diff = (loc1["lng"] - loc2["lng"]) * 111000 * math.cos(math.radians(loc1["lat"]))
    return math.sqrt(lat_diff**2 + lng_diff**2) / 1000

# ─── A* Search ────────────────────────────────────────────────────────────────
def astar_search(start, goal):
    frontier = PriorityQueue()
    frontier.put((0, start))
    came_from   = {start: None}
    cost_so_far = {start: 0}
    nodes_explored = 0

    while not frontier.empty():
        _, current = frontier.get()
        nodes_explored += 1

        if current == goal:
            break

        for neighbor, edge_cost in GRAPH.get(current, []):
            new_cost = cost_so_far[current] + edge_cost
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + heuristic(neighbor, goal)
                frontier.put((priority, neighbor))
                came_from[neighbor] = current

    # Reconstruct path
    path, current = [], goal
    while current is not None:
        path.append(current)
        current = came_from.get(current)
    path.reverse()

    return path, cost_so_far.get(goal, 0), nodes_explored

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template(
        'index.html',
        locations=sorted(LOCATIONS.keys()),
        locations_dict=LOCATIONS
    )

@app.route('/find_path', methods=['POST'])
def find_path():
    data        = request.json
    start       = data.get('start')
    destination = data.get('destination')

    if not start or not destination:
        return jsonify({'error': 'Missing parameters'}), 400

    if start not in LOCATIONS or destination not in LOCATIONS:
        return jsonify({'error': 'Invalid location'}), 400

    path, distance, nodes_explored = astar_search(start, destination)

    coordinates = [
        {'lat': LOCATIONS[node]['lat'], 'lng': LOCATIONS[node]['lng'], 'name': node}
        for node in path
    ]

    return jsonify({
        'algorithm':      'A* Search',
        'path':           path,
        'distance':       round(distance, 2),
        'nodes_explored': nodes_explored,
        'coordinates':    coordinates,
    })

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    data    = request.json
    name    = data.get('name')
    email   = data.get('email')
    comment = data.get('comment')

    if not name or not email or not comment:
        return jsonify({'success': False, 'message': 'Missing fields'}), 400

    try:
        msg             = MIMEMultipart()
        msg['From']     = SENDER_EMAIL
        msg['To']       = RECEIVER_EMAIL
        msg['Subject']  = f"Campus Navigator Feedback from {name}"
        msg.attach(MIMEText(f"Name: {name}\nEmail: {email}\n\nFeedback:\n{comment}", 'plain'))

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

        return jsonify({'success': True, 'message': 'Feedback sent!'})

    except Exception as e:
        print(f"SMTP Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
