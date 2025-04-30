import csv
import sys

def main():
    if len(sys.argv) < 5: 
        print("Usage: python script.py <input_file.csv> <frequency> <datarate> <size>")
        return

    input_file_name = sys.argv[1]
    frequency = float(sys.argv[2])
    datarate = int(sys.argv[3])
    size = float(sys.argv[4])

    output_file_name = "clean_" + input_file_name

    with open(input_file_name, 'rb') as input_file, open(output_file_name, 'wb') as output_file:
        reader = csv.reader(input_file)
        writer = csv.writer(output_file)

        # Read header
        header = next(reader)
        freq_col = header.index('frequency')
        dr_col = header.index('datarate')
        size_col = header.index('size')

        # Write header to output file
        writer.writerow(header)

        # Process each row
        for row in reader:
            try:
                row_freq = float(row[freq_col])
                row_datarate = int(row[dr_col][2:])  # Skip "SF" prefix
                row_size = float(row[size_col])
                if row_freq == frequency and row_datarate == datarate and row_size == size:
                    writer.writerow(row)
            except (ValueError, IndexError):
                # Skip rows with invalid data or missing columns
                pass

    print("Output file created:", output_file_name)

if __name__ == "__main__":
    main()

