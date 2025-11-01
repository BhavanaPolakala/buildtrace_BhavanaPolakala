# app/simulator.py
import json, random

def generate_drawing(version_id, n=5):
    objs = []
    for i in range(n):
        objs.append({
            "id": f"{version_id}_{i}",
            "type": random.choice(["wall", "door", "window"]),
            "x": random.randint(0, 20),
            "y": random.randint(0, 20),
            "width": random.randint(1, 5),
            "height": random.randint(1, 3),
        })
    return objs

if __name__ == "__main__":
    old = generate_drawing("A", 5)
    new = generate_drawing("B", 6)
    with open("data_old.json", "w") as f: json.dump(old, f, indent=2)
    with open("data_new.json", "w") as f: json.dump(new, f, indent=2)
    print("Generated data_old.json and data_new.json")
