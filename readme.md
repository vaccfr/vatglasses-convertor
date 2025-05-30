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

You can use the script `export_geojson.py` to generate GeoJSON file and visualize them with https://geojson.io/

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

## GeoJSON exports

The current VatGlasses data are pre-exported in GeoJSON format and stored in the `exports` folder. You can use the following links to visualize the data in geojson.io:

| FL  | x10 | x20 | x30 | x40 | x50 | x60 | x70 | x80 | x90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3xx | [FL300](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl300.geojson) | [FL310](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl310.geojson) | [FL320](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl320.geojson) | [FL330](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl330.geojson) | [FL340](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl340.geojson) | [FL350](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl350.geojson) | [FL360](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl360.geojson) | [FL370](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl370.geojson) | [FL380](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl380.geojson) | [FL390](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl390.geojson) |
| 2xx | [FL200](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl200.geojson) | [FL210](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl210.geojson) | [FL220](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl220.geojson) | [FL230](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl230.geojson) | [FL240](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl240.geojson) | [FL250](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl250.geojson) | [FL260](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl260.geojson) | [FL270](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl270.geojson) | [FL280](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl280.geojson) | [FL290](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl290.geojson) |
| 1xx | [FL100](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl100.geojson) | [FL110](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl110.geojson) | [FL120](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl120.geojson) | [FL130](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl130.geojson) | [FL140](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl140.geojson) | [FL150](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl150.geojson) | [FL160](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl160.geojson) | [FL170](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl170.geojson) | [FL180](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl180.geojson) | [FL190](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl190.geojson) |
| 0xx | [FL000](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl0.geojson) | [FL010](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl10.geojson) | [FL020](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl20.geojson) | [FL030](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl30.geojson) | [FL040](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl40.geojson) | [FL050](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl50.geojson) | [FL060](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%vatglasses-convertor%2Fmain%2Fexports%2Fctr_fl60.geojson) | [FL070](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl70.geojson) | [FL080](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl80.geojson) | [FL090](https://geojson.io/#data=data:text/x-url,https%3A%2F%2Fraw.githubusercontent.com%2Fvaccfr%2Fvatglasses-convertor%2Fmain%2Fexports%2Fctr_fl90.geojson) |

## Publish to VATGlasses

Copy the file `outputs/lf.json` into the repository `vaccfr/vatglasses-data/data` and submit a PR.