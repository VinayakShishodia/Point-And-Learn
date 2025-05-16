import pickle

# Example data
data = {'key': 'value'}

# Path to the pickle file
file_path = 'countries0.p'

# Write data to the pickle file
with open(file_path, 'wb') as file:
    pickle.dump(data, file)

print(f"Data has been written to {file_path}")
