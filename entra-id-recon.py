#!/usr/bin/env python3

import argparse
import requests
import json
import re
from dns import resolver, exception
from prettytable import PrettyTable
import xml.etree.ElementTree as ET
from termcolor import cprint
import pyfiglet
import pandas as pd
import csv
import xlsxwriter

# Credit for idea and Powershell code goes to Author of AADInternals, Nestori Syynimaa (@DrAzureAD), for which this script would not have been possible: https://github.com/Gerenios/AADInternals

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def display_banner():
    banner = pyfiglet.figlet_format("EntraIDRecon.py")
    cprint(banner, 'green')

def resolve_dns(domain, record_type):
    try:
        answers = resolver.resolve(domain, record_type)
        return [str(rdata) for rdata in answers]
    except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.Timeout, exception.DNSException):
        return []

def get_tenant_id(domain):
    openid_config_url = f"https://login.microsoftonline.com/{domain}/.well-known/openid-configuration"
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(openid_config_url, headers=headers)
    
    if response.status_code == 200:
        tenant_info = response.json()
        issuer_url = tenant_info.get('issuer')
        tenant_id = issuer_url.split('/')[-2] if issuer_url else None
        return tenant_id, tenant_info.get('tenant_region_scope')
    else:
        return None, None

def get_tenant_brand_and_sso(domain):
    user_realm_url = f"https://login.microsoftonline.com/GetUserRealm.srf?login={domain}"
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(user_realm_url, headers=headers)
    
    if response.status_code == 200:
        login_info = response.json()
        brand_name = login_info.get('FederationBrandName', None)
        
        # Checking Desktop SSO
        credential_type_url = f"https://login.microsoftonline.com/common/GetCredentialType"
        body = {"Username": domain}
        response_credential = requests.post(credential_type_url, json=body, headers=headers)
        
        if response_credential.status_code == 200:
            credential_info = response_credential.json()
            desktop_sso_enabled = credential_info.get('EstsProperties', {}).get('DesktopSsoEnabled', False)
        else:
            desktop_sso_enabled = False
        
        return brand_name, desktop_sso_enabled
    else:
        return None, None

def get_tenant_domains(domain):
    openid_config_url = f"https://login.microsoftonline.com/{domain}/.well-known/openid-configuration"
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(openid_config_url, headers=headers)
    
    if response.status_code == 200:
        tenant_info = response.json()
        tenant_region_sub_scope = tenant_info.get('tenant_region_sub_scope')
        
        if tenant_region_sub_scope == "DOD":
            autodiscover_url = "https://autodiscover-s-dod.office365.us/autodiscover/autodiscover.svc"  # DoD
        elif tenant_region_sub_scope == "DODCON":
            autodiscover_url = "https://autodiscover-s.office365.us/autodiscover/autodiscover.svc"  # GCC-High
        else:
            autodiscover_url = "https://autodiscover-s.outlook.com/autodiscover/autodiscover.svc"  # Commercial/WW
    else:
        return None

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": '"http://schemas.microsoft.com/exchange/2010/Autodiscover/Autodiscover/GetFederationInformation"',
        "User-Agent": "AutodiscoverClient"
    }
    
    body = f"""
    <soap:Envelope xmlns:exm="http://schemas.microsoft.com/exchange/services/2006/messages" xmlns:ext="http://schemas.microsoft.com/exchange/services/2006/types" xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Header>
            <a:Action soap:mustUnderstand="1">http://schemas.microsoft.com/exchange/2010/Autodiscover/Autodiscover/GetFederationInformation</a:Action>
            <a:To soap:mustUnderstand="1">{autodiscover_url}</a:To>
            <a:ReplyTo>
                <a:Address>http://www.w3.org/2005/08/addressing/anonymous</a:Address>
            </a:ReplyTo>
        </soap:Header>
        <soap:Body>
            <GetFederationInformationRequestMessage xmlns="http://schemas.microsoft.com/exchange/2010/Autodiscover">
                <Request>
                    <Domain>{domain}</Domain>
                </Request>
            </GetFederationInformationRequestMessage>
        </soap:Body>
    </soap:Envelope>
    """
    
    response = requests.post(autodiscover_url, data=body.encode('utf-8'), headers=headers)
    
    if response.status_code == 200:
        try:
            root = ET.fromstring(response.content)
            namespaces = {
                's': 'http://schemas.xmlsoap.org/soap/envelope/',
                'a': 'http://www.w3.org/2005/08/addressing',
                'm': 'http://schemas.microsoft.com/exchange/2010/Autodiscover',
                't': 'http://schemas.microsoft.com/exchange/2010/Autodiscover'
            }
            domains_element = root.find('.//t:Domains', namespaces)
            domain_list = [d.text for d in domains_element.findall('.//t:Domain', namespaces)]
            
            if domain not in domain_list:
                domain_list.append(domain)
            
            return domain_list
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            return None
    else:
        return None

def get_user_realm_extended(username):
    user_realm_url = f"https://login.microsoftonline.com/GetUserRealm.srf?login={username}"
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(user_realm_url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return None

def get_login_information(username):
    user_realm_url = f"https://login.microsoftonline.com/GetUserRealm.srf?login={username}"
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(user_realm_url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None

def get_credential_type_info(username):
    credential_type_url = f"https://login.microsoftonline.com/common/GetCredentialType"
    body = {
        "username": username,
        "isOtherIdpSupported": True,
        "checkPhones": True,
        "isRemoteNGCSupported": False,
        "isCookieBannerShown": False,
        "isFidoSupported": False,
        "originalRequest": None,
        "flowToken": None
    }
    headers = {"User-Agent": USER_AGENT}
    response = requests.post(credential_type_url, json=body, headers=headers)
        
    if response.status_code == 200:
        return response.json()
    else:
        return None

def save_output(data, domain_data, base_filename, formats, is_user_enum=False):
    output_data = {"user_list" if is_user_enum else "tenant_info": data}
    if not is_user_enum:
        output_data["domain_data"] = domain_data

    if "json" in formats or "all" in formats:
        with open(f"{base_filename}.json", 'w') as f:
            json.dump(output_data, f, indent=4)
    if "txt" in formats or "all" in formats:
        with open(f"{base_filename}.txt", 'w') as f:
            if is_user_enum:
                for result in data:
                    f.write(f"username: {result['username']}, exists: {result['exists']}\n")
            else:
                if domain_data:
                    f.write("Tenant Information:\n")
                    for key, value in data.items():
                        if isinstance(value, list):
                            f.write(f"{key}:\n")
                            for item in value:
                                f.write(f"  - {item}\n")
                        else:
                            f.write(f"{key}: {value}\n")
                    f.write("\nDomain Data:\n")
                    for item in domain_data:
                        for key, value in item.items():
                            f.write(f"{key}: {value}\n")
                        f.write("\n")
                else:
                    for result in data:
                        f.write(f"username: {result['username']}, exists: {result['exists']}\n")
    if "csv" in formats or "all" in formats:
        with open(f"{base_filename}.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            if is_user_enum:
                writer.writerow(["UserName", "Exists"])
                for result in data:
                    writer.writerow([result["username"], result["exists"]])
            else:
                writer.writerow(["Tenant Information"])
                if isinstance(data, list):
                    writer.writerow(data[0].keys())
                    for row in data:
                        writer.writerow(row.values())
                else:
                    writer.writerow(data.keys())
                    writer.writerow(data.values())
                writer.writerow([])
                if domain_data:
                    writer.writerow(["Domain Information"])
                    writer.writerow(domain_data[0].keys())
                    for row in domain_data:
                        writer.writerow(row.values())
    if "xlsx" in formats or "all" in formats:
        with pd.ExcelWriter(f"{base_filename}.xlsx", engine='xlsxwriter') as writer:
            if is_user_enum:
                df_users = pd.DataFrame(data)
                df_users.to_excel(writer, sheet_name='User Info', index=False)
            else:
                df_tenant = pd.DataFrame([data])
                df_tenant.to_excel(writer, sheet_name='Tenant Info', index=False)
                if domain_data:
                    df_domain = pd.DataFrame(domain_data)
                    df_domain.to_excel(writer, sheet_name='Domain Info', index=False)

def aadint_recon_as_outsider(domain, output_file, output_extension):
    tenant_id, tenant_region = get_tenant_id(domain)
    tenant_brand, desktop_sso_enabled = get_tenant_brand_and_sso(domain)

    if not tenant_id:
        print("Failed to retrieve tenant information.")
        return

    login_info = get_login_information(domain)
    if not login_info:
        print("Failed to retrieve login information.")
        return

    dns_mx = resolve_dns(domain, 'MX')
    dns_txt = resolve_dns(domain, 'TXT')

    tenant_info = {
        "tenant_id": tenant_id,
        "tenant_brand": tenant_brand,
        "tenant_region": tenant_region,
        "desktop_sso_enabled": desktop_sso_enabled,
        "login_info": login_info,
        "dns_mx": dns_mx,
        "dns_txt": dns_txt
    }

    table = PrettyTable()
    table.field_names = ["Tenant ID", "Tenant Name", "Tenant Brand", "Tenant Region", "Desktop SSO Enabled"]
    table.add_row([
        tenant_id,
        login_info.get('DomainName'),
        tenant_brand,
        tenant_region,
        desktop_sso_enabled
    ])
    print(table)

    domain_list = get_tenant_domains(domain)
    domain_data = []
    if domain_list:
        domain_table = PrettyTable()
        domain_table.field_names = ["Name", "DNS", "MX", "SPF", "Type", "STS"]
        for name in domain_list:
            dns = bool(resolve_dns(name, 'A'))
            mx = bool("mail.protection.outlook.com" in [x.lower() for x in resolve_dns(name, 'MX')])
            spf = bool(any("spf.protection.outlook.com" in txt for txt in resolve_dns(name, 'TXT')))
            identity_type = "Federated" if name != domain else "Managed"
            sts = f"sts.{name}" if identity_type == "Federated" else ""
            domain_table.add_row([name, dns, mx, spf, identity_type, sts])
            domain_data.append({
                "Name": name,
                "DNS": dns,
                "MX": mx,
                "SPF": spf,
                "Type": identity_type,
                "STS": sts
            })
        print(domain_table)

    if output_file:
        base_filename, ext = output_file.rsplit('.', 1) if '.' in output_file else (output_file, 'txt')
        formats = [ext] if output_extension == "" else [output_extension]
        save_output(tenant_info, domain_data, base_filename, formats)

def aadint_user_enum_as_outsider(username, output_file, input_file, method, output_extension):
    if input_file:
        with open(input_file, 'r') as f:
            usernames = [line.strip() for line in f if line.strip()]
    else:
        if username is None:
            print("Error: Username is required when input file is not provided.")
            return
        if ',' in username:
            usernames = [user.strip() for user in username.split(',')]
        else:
            usernames = [username]

    results = []

    for user in usernames:
        if method == "normal":
            credential_info = get_credential_type_info(user)
            if credential_info:
                if_exists_result = credential_info.get('IfExistsResult', -1)
                exists = if_exists_result == 0 or if_exists_result == 6
            else:
                exists = False
        elif method == "login" or method == "autologon":
            credential_info = get_credential_type_info(user)
            if credential_info:
                if_exists_result = credential_info.get("IfExistsResult", -1)
                exists = if_exists_result == 0 or if_exists_result == 6
            else:
                exists = False

        results.append({"username": user, "exists": exists})

    table = PrettyTable()
    table.field_names = ["UserName", "Exists"]
    for result in results:
        table.add_row([result["username"], result["exists"]])
    print(table)

    if output_file:
        base_filename, ext = output_file.rsplit('.', 1) if '.' in output_file else (output_file, 'txt')
        formats = [ext] if output_extension == "" else [output_extension]
        save_output(results, [], base_filename, formats, is_user_enum=True)

if __name__ == "__main__":
    display_banner()
    
    parser = argparse.ArgumentParser(description="AADInternals Invoke-AADIntReconAsOutsider and Invoke-AADIntUserEnumerationAsOutsider rewritten in Python3")
    subparsers = parser.add_subparsers(dest="command")

    # Subparser for recon
    recon_parser = subparsers.add_parser("entra-external-recon", help="Gather tenancy information based on an input target domain")
    recon_parser.add_argument("-d", "--domain", required=True, help="Domain name (example: example.com)")
    recon_parser.add_argument("-o", "--output", help="Output filename without extension")
    recon_parser.add_argument("-e", "--extension", choices=["txt", "json", "csv", "xlsx", "all"], default="", help="Output format")

    # Subparser for user enumeration
    enum_parser = subparsers.add_parser("entra-external-enum", help="Verifies whether a single or multiple emails are active within an organisation")
    enum_parser.add_argument("-u", "--username", help="Username (example: user@example.com)")
    enum_parser.add_argument("-o", "--output", help="Output filename filename without extension")
    enum_parser.add_argument("-f", "--file", help="Input file with list of email addresses")
    enum_parser.add_argument("-e", "--extension", choices=["txt", "json", "csv", "xlsx", "all"], default="", help="Output format")
    enum_parser.add_argument("-m", "--method", choices=["normal", "login", "autologon"], default="normal", help="Login method")

    args = parser.parse_args()

    if args.command == "entra-external-recon":
        aadint_recon_as_outsider(args.domain, args.output, args.extension)
    elif args.command == "entra-external-enum":
        aadint_user_enum_as_outsider(args.username, args.output, args.file, args.method, args.extension)
    else:
        parser.print_help()
