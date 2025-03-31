from flask import Flask, jsonify, render_template, request
import numpy as np
import polars as pl
import torch
import itertools
import argparse
import random
import pathlib

path = pathlib.Path(__file__).resolve().parent

app = Flask(__name__)

def generate_sample_data(combinations, num_samples=10000):
    return [random.choice(combinations) for _ in range(num_samples)]

def calculate_frequency_and_uniqueness(combinations, samples):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Create a tensor to store frequencies
    freq_tensor = torch.zeros(len(combinations), device=device)
    
    # Calculate frequencies
    for sample in samples:
        if sample in combinations:
            index = combinations.index(sample)
            freq_tensor[index] += 1
    
    # Calculate uniqueness (inverse of frequency)
    uniqueness_tensor = 1 / (freq_tensor + 1)  # Adding 1 to avoid division by zero
    
    # Calculate value score (product of frequency and uniqueness)
    value_score = freq_tensor * uniqueness_tensor
    
    return freq_tensor, uniqueness_tensor, value_score

@app.route('/api/outfit_inventory')
def get_outfit_inventory():
    total_items = 1000  # Total number of items in the inventory

    # Get the valuable combinations data
    valuable_combinations = get_valuable_combinations().json
    outfits = valuable_combinations['outfits']

    # Calculate total value score
    total_value_score = sum(outfit['value_score'] for outfit in outfits)

    # Calculate the number of each outfit in the inventory
    inventory = []
    remaining_items = total_items

    for outfit in outfits:
        # Calculate the proportion of this outfit based on its value score
        proportion = outfit['value_score'] / total_value_score
        
        # Calculate the number of this outfit to include in the inventory
        count = int(proportion * total_items)
        
        # Ensure we don't exceed the remaining items
        count = min(count, remaining_items)
        
        if count > 0:
            inventory.append({
                "outfit": outfit['outfit'],
                "count": count,
                "frequency": outfit['frequency'],
                "uniqueness": outfit['uniqueness'],
                "value_score": outfit['value_score']
            })
            remaining_items -= count

    # If we have any remaining items, distribute them to the outfits with the highest value scores
    if remaining_items > 0:
        sorted_outfits = sorted(inventory, key=lambda x: x['value_score'], reverse=True)
        for outfit in sorted_outfits:
            if remaining_items > 0:
                outfit['count'] += 1
                remaining_items -= 1
            else:
                break

    # Sort the inventory by count in descending order
    inventory.sort(key=lambda x: x['count'], reverse=True)

    return jsonify({
        "total_items": total_items,
        "actual_total": sum(outfit['count'] for outfit in inventory),
        "inventory": inventory
    })
@app.route('/api/valuable_combinations')
def get_valuable_combinations():
    items = [{"coats": ["leather", "fur", "puffy"],
             "hats": ["big", "cowboy", "beanie"], 
             "pants": ["baggy", "tight", "ripped"],
             "shoes": ["running", "dress", "slippers"]}
            ]

    # Generate all possible outfits (one item from each category)
    outfits = list(itertools.product(
        [f"{coat} coat" for coat in items[0]["coats"]],
        [f"{hat} hat" for hat in items[0]["hats"]],
        [f"{pant} pants" for pant in items[0]["pants"]],
        [f"{shoe} shoes" for shoe in items[0]["shoes"]]
    ))

    # Generate sample data
    samples = generate_sample_data(outfits, num_samples=10000)

    # Calculate frequency and uniqueness
    freq_tensor, uniqueness_tensor, value_score = calculate_frequency_and_uniqueness(outfits, samples)

    # Prepare results
    results = []
    for i, outfit in enumerate(outfits):
        results.append({
            "outfit": list(outfit),
            "frequency": int(freq_tensor[i].item()),  # Convert to integer
            "uniqueness": uniqueness_tensor[i].item(),
            "value_score": value_score[i].item()
        })

    # Sort results by frequency in descending order
    results.sort(key=lambda x: x["frequency"], reverse=True)

    return jsonify({
        "outfits": results,
        "total_outfits": len(results),
        "total_samples": len(samples)
    })

@app.route('/api/data')
def get_data():
    data_path = str(path).split("interface")[0]
    df = pl.read_json(f"{data_path}/data.json")
    result = df.to_dicts()
    res = jsonify(result)
    res.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    res.headers['Pragma'] = 'no-cache'
    res.headers['Expires'] = '0'
    return res

@app.route('/')
def index():
    data_path = str(path).split("interface")[0]
    df = pl.read_json(f"{data_path}/data.json")
    data = df.to_dicts()
    return render_template('index.html', data=data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Flask app with a custom port.')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the app on (default: 5000)')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)