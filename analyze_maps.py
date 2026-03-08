import os
import glob

##comment Map values to ASCII art icons
##comment 0 = Empty, 1 = Wall, 2 = Titanium, 3 = Axionite
TERRAIN_ICONS = {
    0: ".",
    1: "#",
    2: "T",
    3: "A"
}

def analyze_maps():
    map_files = glob.glob("maps/*.map26")
    output_filename = "MAP_ANALYSIS.txt"
    
    with open(output_filename, "w", encoding="utf-8") as out:
        out.write("=========================================\n")
        out.write("====== BATTLECODE MAP ANALYSIS ==========\n")
        out.write("=========================================\n\n")
        out.write("LEGEND:\n")
        out.write(" . = Empty Dirt\n")
        out.write(" # = Wall / Unpassable\n")
        out.write(" T = Titanium Ore\n")
        out.write(" A = Axionite Ore\n\n")
        
        for mf in sorted(map_files):
            with open(mf, "rb") as f:
                data = f.read()
                
##comment Maps are stored as protobufs. 
##comment We can extract the dimensions via tag 1 and tag 2
##comment 0x08 is tag 1 (width), 0x10 is tag 2 (height)
            width = data[data.find(b'\x08') + 1]
            height = data[data.find(b'\x10') + 1]
            
##comment The rows are nested messages containing byte arrays of length `width`
##comment Look for the signature: 0x0A (tag 1), followed by the width
##comment E.g., for width 20, it is \x0A\x14
            row_signature = bytes([0x0A, width])
            
            rows = []
            idx = 0
            while len(rows) < height:
                idx = data.find(row_signature, idx)
                if idx == -1:
                    break
##comment Extract the row
                row_bytes = data[idx + 2 : idx + 2 + width]
                rows.append(row_bytes)
                idx += 2 + width

##comment Count statistics
            stats = {0:0, 1:0, 2:0, 3:0}
            for row in rows:
                for b in row:
                    if b in stats:
                        stats[b] += 1
                        
            out.write(f"--- MAP: {os.path.basename(mf)} ---\n")
            out.write(f"Dimensions: {width} x {height}\n")
            out.write(f"Titanium Deposits: {stats[2]}\n")
            out.write(f"Axionite Deposits: {stats[3]}\n")
            out.write(f"Wall Blocks:       {stats[1]}\n")
            out.write(f"Open Space:        {stats[0]}\n\n")
            
##comment Draw ASCII Map
            out.write("+" + "-" * width + "+\n")
            for row in rows:
                row_str = "".join([TERRAIN_ICONS.get(b, "?") for b in row])
                out.write("|" + row_str + "|\n")
            out.write("+" + "-" * width + "+\n\n\n")
            
    print(f"Ô£à Extracted map data to {output_filename}")

if __name__ == "__main__":
    analyze_maps()
