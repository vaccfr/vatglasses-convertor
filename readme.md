# Euroscope ESE to VATGlasses convertor

## File structure

The final target file is `outputs/lf.json`. Each section of that json are generated in separate files first:

| `lf.json` section | File | Type | Script
|---| ---| --- | --- |
| `airports` | `outputs/airports.json` | Dynamic | `generate_airports.py`
| `airspace` | `outputs/airspace.json` | Dynamic | `generate_airspaces.py`
| `callsigns` | `outputs/callsigns.json` | Static |
| `groups` | `outputs/groups.json` | Static |
| `positions` | `outputs/positions.json` | Dynamic |  `generate_positions.py`

The script `merge_all.py` takes all 5 above files and merge them into `outputs/lf.json`


## Install the prerequisites

- Install the required python libraries:
```
pip install -r requirements.txt
```

- Copy the latest Euroscope ESE files in `inputs\LFXX.ese`

## Generate the target files

- Run the following command to generate the `outputs/airports.json`
```
python generate_airports.py
```

- Run the following command to generate the `outputs/airspaces.json`
```
python generate_airspaces.py
```

- Run the following command to generate the `outputs/positions.json`
```
python generate_positions.py
```

- Run the following command to generate the target `outputs/lf.json`
```
python merge_all.py
```

## Test the results

You can use the script `export_geojson.py` to generate GEOJson file and visualize them with https://geojson.io/

```
usage: export_geojson.py [-h] --input-files [INPUT_FILES ...] [--output-file OUTPUT_FILE] [--show] --flight-level FLIGHTLEVEL [--positions [POSITIONS ...]] [--sector-regexp SECTOR_REGEXP]

optional arguments:
  -h, --help            show this help message and exit
  --input-files [INPUT_FILES ...], -i [INPUT_FILES ...]
                        VATGlass input file
  --output-file OUTPUT_FILE, -o OUTPUT_FILE
                        GeoJSON output file
  --show, -s            Show on geojson.io
  --flight-level FLIGHTLEVEL, -f FLIGHTLEVEL
                        Flight Level
  --positions [POSITIONS ...], -p [POSITIONS ...]
                        Space separated list of position codes
  --sector-regexp SECTOR_REGEXP
                        Regular Express to filter sector
```

For example:
- All positions at FL300 (will generate only CTR positions)
``` 
python export_geojson.py -i outputs/lf.json -o output.geojson --flight-level 320
```

- PAR and PG approach at FL180
```
python export_geojson.py -i outputs/lf.json -o output.geojson --flight-level 180 --positions PAR PGN
```

- Marseille, Nice Approach and Tower at 1000 feet
```
python export_geojson.py -i outputs/lf.json -o output.geojson --flight-level 10 --positions MM MNA MN
```

## Publish to VATGlasses

Copy the file `outputs/lf.json` into the repository `vaccfr/vatglasses-data/data` and submit a PR.