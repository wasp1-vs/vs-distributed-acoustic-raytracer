import json
import glob


all_delays = []
all_pressures = []

for f in sorted(glob.glob("/home/manager/ir_node*.json")):
    with open(f) as file:
       data = json.load(file)
       all_delays += data["hits"]["delays_seconds"]
       all_pressures += data["hits"]["pressures"]
    print(f"Geladen: {f}")


merged = {
    "metadata": {
         "sample_rate": 44100,
         "rays_cast": 1000000 * 8,
         "rays_received": len(all_delays),
         "room_name": "MVP_Test_Room_1"
     },
     "hits": {
           "delays_seconds": all_delays,
           "pressures": all_pressures
     }

}


with open("/home/manager/ir_merged.json", "w") as f:
     json.dump(merged, f, indent=2)


print(f"Fertig! {len(all_delays)} hits gesamt in ir_merged.json")
