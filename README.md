# Entra-ID-Recon.py
Entra-ID-Recon.py is a Python script that reimplements some of the reconnaissance and user enumeration functionalities found within the AADInternals project. This script allows you to gather information about Entra-ID tenants and enumerate users to check their existence within an organisation, all from a Nix shell. You could use it on Windows as well, but this script becomes redundant in this context, because you can just use the original powershell code - seriously it has a lot more to offer:

#### Original source code and documentation
- https://github.com/Gerenios/AADInternals
- https://aadinternals.com/aadinternals/

## Credits
This script is inspired by the original AADInternals project created by Nestori Syynimaa (@DrAzureAD). All ideas and code belong to the original author, this script is a reimplemnation of a very small subet of the original project and was created for educational purposes.

## Disclaimer
- This tool was created for the authors personal learning and for educational purposes, never run this script against an organisation in which you do not have explicit, written permission to conduct a legitimate security audit against.
- **Warning:** the 'login' verification method will be detailed within the target tenants Audit logs, tread carefully.

## Features
- Retrieve a target domains tenant ID, company brand name, tenant region, and whether Seamless SSO is supported.
- Enumerate email addresses and validate whether they are active within the target organisation.
- Save output in various formats: JSON, CSV, XLSX, and TXT are supported.

## Requirements
- Python 3.x
- Required Python modules listed in `requirements.txt`.

## Installation
1. Clone this repository.
2. Install the required Python modules:
    ``` python
    pip install -r requirements.txt
    ```

## Usage
The script has two main functionalities: external recon and user enumeration. Below are the command-line options for each functionality.

### External Recon - Retrieve information about an Entra-ID tenant.

#### Command:
``` python
python3 entra-id-recon.py entra-external-recon -d <domain> [-o <output_file>] [-e <extension>]
```
##### Options:
- -d, --domain: Domain name (example: example.com) [Required]
- -o, --output: Output filename [Optional]
- -e, --extension: Output format (choices: txt, json, csv, xlsx, all) [Optional] Note: the default format will be .txt if -e is not specified

#### Examples:
##### Basic usage
``` python
python3 entra-id-recon.py entra-external-recon -d example.com
```

##### Output to specific file and format
``` python
python3 entra-id-recon.py entra-external-recon -d example.com -o outputfile -e json
```
##### Output in all formats
``` python
python3 entra-id-recon.py entra-external-recon -d example.com -o outputfile -e all
```
### User Enumeration - Check the existence of users in an Entra-ID tenant.

#### Command:
``` python
python3 entra-id-recon.py entra-external-enum [-u <username>] [-o <output_file>] [-f <input_file>] [-e <extension>] [-m <method>]
```
##### Options:
- -u, --username: Username (example: user@example.com) [Optional]
- -o, --output: Output filename without extension [Optional]
- -f, --file: Input file with a list of email addresses [Optional]
- -e, --extension: Output format (choices: txt, json, csv, xlsx, all) [Optional] Note: the default format will be .txt if -e is not specified
- -m, --method: Login method (choices: normal, login, autologon) [Optional, default: normal]

#### Examples:
###### Check a single user
``` python
python3 entra-id-recon.py entra-external-enum -u user@example.com
```
##### Check multiple users
``` python
python3 entra-id-recon.py entra-external-enum -u "user1@example.com,user2@example.com"
```
##### Check users from an input file
``` python
python3 entra-id-recon.py entra-external-enum -f user-list.txt
```
##### Output results to a specific file and format
``` python
python3 entra-id-recon.py entra-external-enum -u user@example.com -o outputfile -e json
```
##### Use the login method for enumeration
``` python
python3 entra-id-recon.py entra-external-enum -u user@example.com -m login
```
### Technical details and further reading
- Please see original project documentation and source code for more information regarding the internals of the API's leveraged by both this script and the original AADInternals codebase.
- https://aadinternals.com/aadinternals/
- https://aadinternals.com/post/just-looking/
- https://aadinternals.com/post/desktopsso/
- https://github.com/Gerenios/AADInternals