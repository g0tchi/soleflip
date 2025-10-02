"""
Execute Bulk Sync with Collected Sales Data
Syncs all StockX sales from Notion to PostgreSQL

This script contains sales data collected from Notion MCP search results.
Run with --dry-run first to validate, then execute for real sync.

Usage:
    python execute_bulk_sync.py --dry-run   # Validate first
    python execute_bulk_sync.py             # Real sync
"""
import asyncio
import sys
from typing import Dict, Optional
import structlog

from sync_notion_to_postgres import NotionPostgresSyncService

logger = structlog.get_logger(__name__)


def parse_sale_from_highlight(highlight: str, title: str, url: str) -> Optional[Dict]:
    """Parse Notion search highlight into sale properties dict"""
    props = {}

    # Parse each line
    for line in highlight.split('\n'):
        if ': ' not in line:
            continue

        parts = line.split(': ', 1)
        if len(parts) != 2:
            continue

        field, value = parts[0].strip(), parts[1].strip()

        # Skip empty values
        if not value or value in ['-', '']:
            continue

        # Parse by field type
        if field == 'Size':
            props['Size'] = value
        elif field == 'Type':
            props['Type'] = value
        elif field == 'Brand':
            props['Brand'] = value
        elif field == 'Supplier':
            props['Supplier'] = value
        elif field == 'Gross Buy':
            props['Gross Buy'] = float(value.replace('€', '').replace(',', '.').strip())
        elif field == 'Gross Sale':
            props['Gross Sale'] = float(value.replace('€', '').replace(',', '.').strip())
        elif field == 'Net Sale':
            props['Net Sale'] = float(value.replace('€', '').replace(',', '.').strip())
        elif field == 'Profit':
            props['Profit'] = float(value.replace('€', '').replace(',', '.').strip())
        elif field == 'ROI':
            props['ROI'] = float(value.replace('%', '').replace(',', '.').strip())
        elif field == 'Shelf Life':
            try:
                props['Shelf Life'] = int(value)
            except:
                props['Shelf Life'] = 0
        elif field == 'VAT?':
            props['VAT?'] = value.lower() == 'true'
        elif field == 'Payout Received?':
            props['Payout Received?'] = value.lower() == 'true'
        elif field == 'Buy Date':
            props['date:Buy Date:start'] = value
        elif field == 'Sale Date':
            props['date:Sale Date:start'] = value
        elif field == 'Delivery Date':
            props['date:Delivery Date:start'] = value
        elif field == 'Sale ID':
            props['Sale ID'] = value.strip()
        elif field == 'Sale Platform':
            props['Sale Platform'] = value
        elif field == 'Order No.':
            props['Order No.'] = value
        elif field == 'Invoice Nr.':
            props['Invoice Nr.'] = value
        elif field == 'Email':
            props['Email'] = value
        elif field == 'Status':
            props['Status'] = value

    # Add SKU from title
    props['SKU'] = title

    return props if props.get('Sale ID') and props.get('Sale Platform') == 'StockX' else None


# Sales data from Notion search results
# Format: (title, url, highlight)
NOTION_SALES_RAW = [
    ('ID8650', 'https://www.notion.so/1b404e82a80746518471f1b307ad33ee',
     '''ID8650
Size: 10.5
Type: US
Buy Date: 2024-07-24
Status: Sale completed
Delivery Date: 2024-07-23
Gross Buy: 127,99 €
VAT?: true
Net Buy: 107,55 €
Supplier: BSTN
Order No.: 13001671992
Invoice Nr.: VR131674973
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-07-24
Sale Platform: StockX
Sale ID: 66088825-65988584
Gross Sale: 124,55 €
Net Sale: 124,55 €
Payout Received?: true
ROI: 13 %
Profit: 17,00 €
Shelf Life: 1
Brand: Adidas'''),

    ('FZ4159-100', 'https://www.notion.so/2a64f394153647e399003a8e2fbdaa09',
     '''FZ4159-100
Size: 8
Type: US
Buy Date: 2024-07-24
Status: Sale completed
Delivery Date: 2024-07-23
Gross Buy: 115,99 €
VAT?: true
Net Buy: 97,47 €
Supplier: BSTN
Order No.: 13001671992
Invoice Nr.: VR131674973
Sale Date: 2024-10-04
Sale Platform: StockX
Sale ID: 68237673-68137432
Gross Sale: 88,48 €
Net Sale: 88,48 €
Payout Received?: true
ROI: -8 %
Profit: -8,99 €
Shelf Life: 73
Brand: Jordan'''),

    ('DZ5485-042', 'https://www.notion.so/46cbf9dce0ed4c86a2b7defc92e92f0e',
     '''DZ5485-042
Size: 10
Type: US
Buy Date: 2024-03-13
Status: Sale completed
Delivery Date: 2024-03-15
Gross Buy: 99,74 €
VAT?: true
Net Buy: 83,82 €
Supplier: Nike
Order No.: C01379032627
Invoice Nr.: DE1023669060
Sale Date: 2024-03-30
Sale Platform: StockX
Sale ID: 62692683-62592442
Gross Sale: 87,37 €
Net Sale: 87,37 €
Payout Received?: true
ROI: 4 %
Profit: 3,55 €
Shelf Life: 15
Brand: Nike'''),

    # Additional sales from search results
    ('DV1892-410', 'https://www.notion.so/90019c0e96544e738c3dff2bd5e2ad6b',
     '''DV1892-410
Size: S
Type: US
Buy Date: 2023-08-30
Status: Sale completed
Delivery Date: 2023-09-01
Gross Buy: 31,20 €
VAT?: true
Supplier: Overkill
Order No.: DE—110857
Invoice Nr.: K1692520
Sale Date: 2023-09-18
Sale Platform: StockX
Sale ID: 55524918-55424677
Gross Sale: 40,86 €
Net Sale: 40,86 €
Payout Received?: true
ROI: 47 %
Profit: 14,64 €
Shelf Life: 17
Brand: Jordan'''),

    ('DV0831-10', 'https://www.notion.so/642a29bfeb55432db15773b482cc177c',
     '''DV0831-10
Size: 12.5
Type: US
Buy Date: 2024-05-13
Status: Sale completed
Delivery Date: 2024-05-03
Gross Buy: 89,99 €
VAT?: true
Supplier: Nike
Order No.: C01396341727
Invoice Nr.: DE1024324677
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-05-08
Sale Platform: StockX
Sale ID: 63861533-63761292
Gross Sale: 90,34 €
Net Sale: 90,34 €
Payout Received?: true
ROI: 16 %
Profit: 14,72 €
Shelf Life: 5
Brand: Nike'''),

    ('A08857C', 'https://www.notion.so/f589b3b6295a4562b9d84428b40ff9f7',
     '''A08857C
Size: 8
Type: US
Buy Date: 2024-06-29
Status: Sale completed
Delivery Date: 2024-07-02
Gross Buy: 65,00 €
VAT?: true
Supplier: Highsnobiety
Order No.: NDEFTGDGMD3
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-07-15
Sale Platform: StockX
Sale ID: 65828054-65727813
Gross Sale: 79,27 €
Net Sale: 79,27 €
Payout Received?: true
ROI: 38 %
Profit: 24,65 €
Shelf Life: 13
Brand: Converse'''),

    ('DZ4507-600', 'https://www.notion.so/5f9f65ffdaba47a9bd65dc3b7f68a17e',
     '''DZ4507-600
Size: 9
Type: US
Buy Date: 2024-07-11
Status: Sale completed
Delivery Date: 2024-07-17
Gross Buy: 89,25 €
VAT?: true
Supplier: Overkill
Order No.: OKI-3105
Invoice Nr.: KI781264
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-07-28
Sale Platform: StockX
Sale ID: 66092698-65992457
Gross Sale: 89,45 €
Net Sale: 89,45 €
Payout Received?: true
ROI: 16 %
Profit: 14,45 €
Shelf Life: 11
Brand: Nike'''),

    ('CT1042-010', 'https://www.notion.so/1402a716dc4380f39e85df109c0b4c5a',
     '''CT1042-010
Size: M
Type: US
Buy Date: 2024-11-08
Status: Sale completed
Delivery Date: 2024-11-13
Gross Buy: 239,60 €
VAT?: true
Supplier: Overkill
Order No.: GA-20398
Email: karmagotchi@gmail.com
Sale Date: 2024-11-06
Sale Platform: StockX
Sale ID: 69162430-69062189
Gross Sale: 286,97 €
Net Sale: 286,97 €
Payout Received?: true
ROI: 36 %
Profit: 85,63 €
Shelf Life: -7
Brand: Nike'''),

    ('DD2858-401', 'https://www.notion.so/5e9755d8401e4bdf897682ab156ec6ab',
     '''DD2858-401
Size: 10
Type: US
Buy Date: 2024-02-13
Status: Sale completed
Delivery Date: 2024-02-20
Gross Buy: 117,75 €
VAT?: true
Supplier: 43einhalb
Order No.: 112957768
Invoice Nr.: 432411709
Email: 3vil@nurfuerspam.de
Sale Date: 2024-05-12
Sale Platform: StockX
Sale ID: 63953796-63853555
Gross Sale: 83,59 €
Net Sale: 83,59 €
Payout Received?: true
ROI: -13 %
Profit: -15,36 €
Shelf Life: 82
Brand: Nike'''),

    ('EK0A5BBES06', 'https://www.notion.so/03a58bfe312c43cb9e33d251cf0f5a17',
     '''EK0A5BBES06
Size:
Type:
Buy Date: 2024-08-13
Status: Sale completed
Gross Buy: 99,99 €
VAT?: true
Supplier: CTBI Trading
Order No.: AL100095983
Invoice Nr.: AL50273696
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-08-13
Sale Platform: StockX
Sale ID: 66796889-66696648
Gross Sale: 102,10 €
Net Sale: 102,10 €
Payout Received?: true
ROI: 18 %
Profit: 18,07 €
Brand: Eastpak'''),

    ('ID8650-v2', 'https://www.notion.so/a39bcede026b4a089f218d536f5bb934',
     '''ID8650
Size: 10
Type: US
Buy Date: 2024-07-24
Status: Sale completed
Delivery Date: 2024-07-23
Gross Buy: 128,00 €
VAT?: true
Supplier: BSTN
Order No.: 13001671992
Invoice Nr.: VR131674973
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-08-28
Sale Platform: StockX
Sale ID: 67317998-67217757
Gross Sale: 115,27 €
Net Sale: 115,27 €
Payout Received?: true
ROI: 6 %
Profit: 7,71 €
Shelf Life: 36
Brand: Adidas'''),

    ('ID3546', 'https://www.notion.so/0407609a7c6b4b7fbb622a59ebdf916c',
     '''ID3546
Size: 11.5
Type: US
Buy Date: 2024-06-29
Status: Sale completed
Delivery Date: 2024-07-02
Gross Buy: 84,00 €
VAT?: true
Supplier: Highsnobiety
Order No.: NDEFTGDGMD3
Invoice Nr.: INV2024TM0173489
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-07-15
Sale Platform: StockX
Sale ID: 65745278-65645037
Gross Sale: 88,27 €
Net Sale: 88,27 €
Payout Received?: true
ROI: 21 %
Profit: 17,68 €
Shelf Life: 13
Brand: Adidas'''),

    ('360001151', 'https://www.notion.so/30a25b873733412b8554eafe98eb7bed',
     '''360001151
Size:
Type:
Buy Date: 2024-08-09
Status: Sale completed
Delivery Date: 2024-08-17
Gross Buy: 55,93 €
VAT?: true
Supplier: Kickz
Order No.: K001-10002069858
Invoice Nr.: RE 6495094
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-08-19
Sale Platform: StockX
Sale ID: 66953915-66853674
Gross Sale: 64,45 €
Net Sale: 64,45 €
Payout Received?: true
ROI: 31 %
Profit: 17,45 €
Shelf Life: 2
Brand: Market'''),

    ('1129958-LSGS', 'https://www.notion.so/641fddec8a134fc1920e704ebb705425',
     '''1129958-LSGS
Size: 8
Type: US
Buy Date: 2024-07-12
Status: Sale completed
Delivery Date: 2024-07-17
Gross Buy: 72,00 €
VAT?: true
Supplier: Highsnobiety
Order No.: NDEPNKTSAQ6
Invoice Nr.: INV2024TM0177484
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-07-21
Sale Platform: StockX
Sale ID: 66003475-65903234
Gross Sale: 84,50 €
Net Sale: 84,50 €
Payout Received?: true
ROI: 33 %
Profit: 24,00 €
Shelf Life: 4
Brand: Hoka'''),

    ('FZ6212', 'https://www.notion.so/1112a716dc4380d8ab1de5d67d46348a',
     '''FZ6212
Size: 13
Type: US
Buy Date: 2024-06-14
Status: Sale completed
Delivery Date: 2024-06-19
Gross Buy: 52,99 €
VAT?: true
Supplier: BestSecret
Order No.: 2116780636
Invoice Nr.: 8025663036
Sale Date: 2024-09-22
Sale Platform: StockX
Sale ID: 68003898-67903657
Gross Sale: 53,62 €
Net Sale: 53,62 €
Payout Received?: true
ROI: 17 %
Profit: 9,09 €
Shelf Life: 95
Brand: Nike'''),

    ('FQ6965-600', 'https://www.notion.so/d0c721655b134ea883fe75ca768925db',
     '''FQ6965-600
Size: 12
Type: US
Buy Date: 2024-08-21
Status: Sale completed
Delivery Date: 2024-08-22
Gross Buy: 72,80 €
VAT?: true
Supplier: 43einhalb
Order No.: 113087132
Invoice Nr.: 432467441
Email: 3vil@nurfuerspam.de
Sale Date: 2024-08-23
Sale Platform: StockX
Sale ID: 67153871-67053630
Gross Sale: 63,96 €
Net Sale: 63,96 €
Payout Received?: true
ROI: 4 %
Profit: 2,78 €
Shelf Life: 1
Brand: Nike'''),

    ('JH9088', 'https://www.notion.so/1372a716dc4380089a6efa3046e2844a',
     '''JH9088
Size: 6
Type: US
Buy Date: 2024-10-27
Status: Sale completed
Delivery Date: 2024-10-30
Gross Buy: 110,00 €
VAT?: true
Supplier: Adidas
Order No.: ADE94128999
Invoice Nr.: DEADIN0036968975
Email: 3vil@nurfuerspam.de
Sale Date: 2024-11-07
Sale Platform: StockX
Sale ID: 69092965-68992724
Gross Sale: 90,66 €
Net Sale: 90,66 €
Payout Received?: true
ROI: -2 %
Profit: -1,78 €
Shelf Life: 8
Brand: Adidas'''),

    ('ID8650-v3', 'https://www.notion.so/ff29c66a1bb24cd58674373e8f1de157',
     '''ID8650
Size: 9.5
Type: US
Buy Date: 2024-07-24
Status: Sale completed
Delivery Date: 2024-07-23
Gross Buy: 127,99 €
VAT?: true
Supplier: BSTN
Order No.: 13001671992
Invoice Nr.: VR131674973
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-09-15
Sale Platform: StockX
Sale ID: 67824179-67723938
Gross Sale: 98,22 €
Net Sale: 98,22 €
Payout Received?: true
ROI: -7 %
Profit: -9,33 €
Shelf Life: 54
Brand: Adidas'''),

    ('DR5274-664', 'https://www.notion.so/121cd61db2b44e95a75b058ddf31d3b4',
     '''DR5274-664
Size:
Type: US
Buy Date: 2024-06-17
Status: Sale completed
Delivery Date: 2024-06-22
Gross Buy: 41,04 €
VAT?: true
Supplier: 43einhalb
Order No.: 113004061
Invoice Nr.: 432449815
Email: 3vil@nurfuerspam.de
Sale Date: 2024-09-02
Sale Platform: StockX
Sale ID: 67457496-67357255
Gross Sale: 22,30 €
Net Sale: 22,30 €
Payout Received?: true
ROI: -30 %
Profit: -12,19 €
Shelf Life: 72
Brand: Nike'''),

    ('CU1727-700-v1', 'https://www.notion.so/3f327159764b49cfad9bf1a8546a8a08',
     '''CU1727-700
Size: 7.5
Type: US
Buy Date: 2024-05-03
Status: Sale completed
Gross Buy: 104,00 €
VAT?: true
Supplier: Solebox
Order No.: 20243723639753
Invoice Nr.: V0000915759
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-05-22
Sale Platform: StockX
Sale ID: 64238718-64138477
Gross Sale: 101,36 €
Net Sale: 101,36 €
Payout Received?: true
ROI: 13 %
Profit: 13,97 €
Brand: Nike'''),

    ('CU1727-700-v2', 'https://www.notion.so/30ae5b7f735a46ae9ff5053d715af130',
     '''CU1727-700
Size: 7.5
Type: US
Buy Date: 2024-05-03
Status: Sale completed
Gross Buy: 104,00 €
VAT?: true
Supplier: Solebox
Order No.: 20243723639753
Invoice Nr.: V0000915759
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-05-15
Sale Platform: StockX
Sale ID: 64037216-63936975
Gross Sale: 97,09 €
Net Sale: 97,09 €
Payout Received?: true
ROI: 9 %
Profit: 9,70 €
Brand: Nike'''),

    ('FJ1214-400-v1', 'https://www.notion.so/39479b921d334e0a8c0df5ca29763f6c',
     '''FJ1214-400
Size: 9
Type: US
Buy Date: 2024-03-13
Status: Sale completed
Delivery Date: 2024-03-15
Gross Buy: 82,49 €
VAT?: true
Supplier: Nike
Order No.: C01378817477
Invoice Nr.: DE1023667064
Email: Carlton-Myslin03@web.de
Sale Date: 2024-03-19
Sale Platform: StockX
Sale ID: 62335033-62234792
Gross Sale: 82,14 €
Net Sale: 82,14 €
Payout Received?: true
ROI: 16 %
Profit: 12,82 €
Shelf Life: 4
Brand: Nike'''),

    ('FD6848-001', 'https://www.notion.so/b45b5c29b0b84a52b67b10e23ab24dad',
     '''FD6848-001
Size: 9.5
Type: US
Buy Date: 2024-04-25
Status: Sale completed
Delivery Date: 2024-05-08
Gross Buy: 139,99 €
VAT?: true
Supplier: BSTN
Order No.: 13001568278
Invoice Nr.: VR131540877
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-07-23
Sale Platform: StockX
Sale ID: 65832275-65732034
Gross Sale: 102,66 €
Net Sale: 102,66 €
Payout Received?: true
ROI: -11 %
Profit: -14,98 €
Shelf Life: 76
Brand: Nike'''),

    ('HN9882', 'https://www.notion.so/0daa397fbc874cb88d2604b71a58ad26',
     '''HN9882
Size: S
Type: US
Buy Date: 2024-05-23
Status: Sale completed
Delivery Date: 2024-05-15
Gross Buy: 177,00 €
VAT?: true
Supplier: BestSecret
Order No.: 2114944617
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-05-23
Sale Platform: StockX
Sale ID: 64078930-63978689
Gross Sale: 201,88 €
Net Sale: 201,88 €
Payout Received?: true
ROI: 30 %
Profit: 53,14 €
Shelf Life: 8
Brand: Adidas'''),

    ('845053-201', 'https://www.notion.so/13d2a716dc4380ee9d62cd0ad52ed205',
     '''845053-201
Size: 10
Type: US
Buy Date: 2024-11-07
Status: Sale completed
Delivery Date: 2024-11-11
Gross Buy: 78,74 €
VAT?: true
Supplier: BSTN
Order No.: 12001654642
Invoice Nr.: VR131861321
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-11-12
Sale Platform: StockX
Sale ID: 69321987-69221746
Gross Sale: 60,20 €
Net Sale: 60,20 €
Payout Received?: true
ROI: -8 %
Profit: -5,97 €
Shelf Life: 1
Brand: Nike'''),

    ('FJ1214-400-v2', 'https://www.notion.so/39fd78c8b2af4cc48c98fe232a30448d',
     '''FJ1214-400
Size: 10
Type: US
Buy Date: 2024-03-13
Status: Sale completed
Delivery Date: 2024-03-15
Gross Buy: 82,49 €
VAT?: true
Supplier: Nike
Order No.: C01378817477
Invoice Nr.: DE1023667064
Email: Carlton-Myslin03@web.de
Sale Date: 2024-03-17
Sale Platform: StockX
Sale ID: 62290956-62190715
Gross Sale: 86,80 €
Net Sale: 86,80 €
Payout Received?: true
ROI: 21 %
Profit: 17,48 €
Shelf Life: 2
Brand: Nike'''),

    # Additional sales from systematic searches (2024-09-30)
    ('IE0421', 'https://www.notion.so/e5c0f44b9bf2414b928ccdf0a3c10a24',
     '''IE0421
Size: 6.5
Type: US
Buy Date: 2024-04-27
Status: Sale completed
Delivery Date: 2024-05-02
Gross Buy: 102,00 €
VAT?: true
Net Buy: 85,71 €
Supplier: Solebox
Order No.: 20243723633805
Invoice Nr.: V0000912268
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-05-10
Sale Platform: StockX
Sale ID: 63910999-63810758
Gross Sale: 93,05 €
Net Sale: 93,05 €
Payout Received?: true
ROI: 7 %
Profit: 7,34 €
Shelf Life: 8
Brand: Adidas'''),

    ('IH2813', 'https://www.notion.so/14a2a716dc43801fbc1cfd1438869c74',
     '''IH2813
Size: 12
Type: US
Buy Date: 2024-11-22
Status: Sale completed
Delivery Date: 2024-11-25
Gross Buy: 94,90 €
VAT?: true
Net Buy: 79,75 €
Supplier: BSTN
Order No.: 13001814012
Invoice Nr.: VR131890054
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-11-25
Sale Platform: StockX
Sale ID: 69731183-69630942
Gross Sale: 100,30 €
Net Sale: 100,30 €
Payout Received?: true
ROI: 22 %
Profit: 20,55 €
Shelf Life: 0
Brand: Adidas'''),

    ('ID3546', 'https://www.notion.so/0407609a7c6b4b7fbb622a59ebdf916c',
     '''ID3546
Size: 11.5
Type: US
Buy Date: 2024-06-29
Status: Sale completed
Delivery Date: 2024-07-02
Gross Buy: 84,00 €
VAT?: true
Net Buy: 70,59 €
Supplier: Highsnobiety
Order No.: NDEFTGDGMD3
Invoice Nr.: INV2024TM0173489
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-07-15
Sale Platform: StockX
Sale ID: 65745278-65645037
Gross Sale: 88,27 €
Net Sale: 88,27 €
Payout Received?: true
ROI: 21 %
Profit: 17,68 €
Shelf Life: 13
Brand: Adidas'''),

    ('1129958-LSGS', 'https://www.notion.so/641fddec8a134fc1920e704ebb705425',
     '''1129958-LSGS
Size: 8
Type: US
Buy Date: 2024-07-12
Status: Sale completed
Delivery Date: 2024-07-17
Gross Buy: 72,00 €
VAT?: true
Net Buy: 60,50 €
Supplier: Highsnobiety
Order No.: NDEPNKTSAQ6
Invoice Nr.: INV2024TM0177484
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-07-21
Sale Platform: StockX
Sale ID: 66003475-65903234
Gross Sale: 84,50 €
Net Sale: 84,50 €
Payout Received?: true
ROI: 33 %
Profit: 24,00 €
Shelf Life: 4
Brand: Hoka'''),

    ('FN6914-400', 'https://www.notion.so/933cd70554ad415cbe33d1e783822a22',
     '''FN6914-400
Size: 8
Type: US
Buy Date: 2024-06-25
Status: Sale completed
Delivery Date: 2024-06-29
Gross Buy: 97,49 €
VAT?: true
Net Buy: 81,92 €
Supplier: Nike
Order No.: C01412031763
Invoice Nr.: DE1024956035
Email: WilfordFormella86@web.de
Sale Date: 2024-06-29
Sale Platform: StockX
Sale ID: 65380307-65280066
Gross Sale: 120,10 €
Net Sale: 120,10 €
Payout Received?: true
ROI: 39 %
Profit: 38,18 €
Shelf Life: 0
Brand: Nike'''),

    ('ID8650-v3', 'https://www.notion.so/a39bcede026b4a089f218d536f5bb934',
     '''ID8650
Size: 10
Type: US
Buy Date: 2024-07-24
Status: Sale completed
Delivery Date: 2024-07-23
Gross Buy: 128,00 €
VAT?: true
Net Buy: 107,56 €
Supplier: BSTN
Order No.: 13001671992
Invoice Nr.: VR131674973
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-08-28
Sale Platform: StockX
Sale ID: 67317998-67217757
Gross Sale: 115,27 €
Net Sale: 115,27 €
Payout Received?: true
ROI: 6 %
Profit: 7,71 €
Shelf Life: 36
Brand: Adidas'''),

    ('DN1856-061', 'https://www.notion.so/785c0071c86c4bf394aa6799bcd430c6',
     '''DN1856-061
Size: 9
Type: US
Buy Date: 2024-03-18
Status: Sale completed
Gross Buy: 64,90 €
VAT?: true
Net Buy: 54,54 €
Supplier: Intersport
Order No.: 13093325
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-06-01
Sale Platform: StockX
Sale ID: 64384486-64284245
Gross Sale: 63,38 €
Net Sale: 63,38 €
Payout Received?: true
ROI: 14 %
Profit: 8,84 €
Brand: Jordan'''),

    ('DV1892-410', 'https://www.notion.so/90019c0e96544e738c3dff2bd5e2ad6b',
     '''DV1892-410
Size: S
Buy Date: 2023-08-30
Status: Sale completed
Delivery Date: 2023-09-01
Gross Buy: 31,20 €
VAT?: true
Net Buy: 26,22 €
Supplier: Overkill
Order No.: DE—110857
Invoice Nr.: K1692520
Sale Date: 2023-09-18
Sale Platform: StockX
Sale ID: 55524918-55424677
Gross Sale: 40,86 €
Net Sale: 40,86 €
Payout Received?: true
ROI: 47 %
Profit: 14,64 €
Shelf Life: 17
Brand: Jordan'''),

    ('FJ1214-100-v2', 'https://www.notion.so/3bd47c8aa7a74dba98c17077c14b2c61',
     '''FJ1214-100
Size: 11.5
Type: US
Buy Date: 2024-07-09
Status: Sale completed
Delivery Date: 2024-07-10
Gross Buy: 82,49 €
VAT?: true
Net Buy: 69,32 €
Supplier: Nike
Order No.: C01416089214
Invoice Nr.: DE1025102138
Email: roccoyambao@web.de
Sale Date: 2024-07-14
Sale Platform: StockX
Sale ID: 65806961-65706720
Gross Sale: 80,17 €
Net Sale: 80,17 €
Payout Received?: true
ROI: 13 %
Profit: 10,85 €
Shelf Life: 4
Brand: Nike'''),

    ('FJ1214-400-v3', 'https://www.notion.so/39479b921d334e0a8c0df5ca29763f6c',
     '''FJ1214-400
Size: 9
Type: US
Buy Date: 2024-03-13
Status: Sale completed
Delivery Date: 2024-03-15
Gross Buy: 82,49 €
VAT?: true
Net Buy: 69,32 €
Supplier: Nike
Order No.: C01378817477
Invoice Nr.: DE1023667064
Email: Carlton-Myslin03@web.de
Sale Date: 2024-03-19
Sale Platform: StockX
Sale ID: 62335033-62234792
Gross Sale: 82,14 €
Net Sale: 82,14 €
Payout Received?: true
ROI: 16 %
Profit: 12,82 €
Shelf Life: 4
Brand: Nike'''),

    ('HJ4320-001', 'https://www.notion.so/1422a716dc4380c284d9c165144e5938',
     '''HJ4320-001
Size: 10
Type: US
Buy Date: 2024-11-09
Status: Sale completed
Delivery Date: 2024-11-12
Gross Buy: 149,99 €
VAT?: true
Net Buy: 126,04 €
Supplier: Nike
Order No.: C01450084739
Invoice Nr.: DE1026064336
Sale Date: 2024-11-14
Sale Platform: StockX
Sale ID: 69377352-69277111
Gross Sale: 164,81 €
Net Sale: 164,81 €
Payout Received?: true
ROI: 26 %
Profit: 38,77 €
Shelf Life: 2
Brand: Nike'''),

    ('ID2350', 'https://www.notion.so/f327c59c40db4605a12a5aac40871d7a',
     '''ID2350
Size: 4
Type: US
Buy Date: 2024-06-26
Status: Sale completed
Delivery Date: 2024-06-14
Gross Buy: 70,00 €
VAT?: true
Net Buy: 58,82 €
Supplier: Adidas
Order No.: ADE91910189
Invoice Nr.: DEADIN0034033859
Email: 3vil@nurfuerspam.de
Sale Date: 2024-06-26
Sale Platform: StockX
Sale ID: 65026161-64925920
Gross Sale: 56,58 €
Net Sale: 56,58 €
Payout Received?: true
ROI: -3 %
Profit: -2,24 €
Shelf Life: 12
Brand: Adidas'''),

    ('BD7632', 'https://www.notion.so/3031ef1b89794485bfd4b8c012093873',
     '''BD7632
Size: 8
Type: US
Buy Date: 2024-03-21
Status: Sale completed
Delivery Date: 2024-03-25
Gross Buy: 88,00 €
VAT?: true
Net Buy: 73,95 €
Supplier: Adidas
Order No.: ADE65435351
Invoice Nr.: DEADIN0032283757
Email: 3vil@nurfuerspam.de
Sale Date: 2024-04-02
Sale Platform: StockX
Sale ID: 62761700-62661459
Gross Sale: 79,27 €
Net Sale: 79,27 €
Payout Received?: true
ROI: 6 %
Profit: 5,32 €
Shelf Life: 8
Brand: Adidas'''),

    ('HQ8717', 'https://www.notion.so/dfbdaf5961fb4f998ad7b639a4d33c8e',
     '''HQ8717
Size: 7.5
Type: US
Buy Date: 2024-08-19
Status: Sale completed
Delivery Date: 2024-08-22
Gross Buy: 89,25 €
VAT?: true
Net Buy: 75,00 €
Supplier: Overkill
Order No.: OKI-11117
Invoice Nr.: KI791082
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-08-23
Sale Platform: StockX
Sale ID: 67219918-67119677
Gross Sale: 79,27 €
Net Sale: 79,27 €
Payout Received?: true
ROI: 5 %
Profit: 4,27 €
Shelf Life: 1
Brand: Adidas'''),

    ('IH2814', 'https://www.notion.so/3235aeb5e1214685b8f46e9a47a2bf73',
     '''IH2814
Size: 9
Type: US
Buy Date: 2024-08-10
Status: Sale completed
Delivery Date: 2024-08-15
Gross Buy: 50,00 €
VAT?: true
Net Buy: 42,02 €
Supplier: Adidas
Order No.: ADE93094716
Invoice Nr.: DEADIN0035591177
Email: 3vil@nurfuerspam.de
Sale Date: 2024-08-28
Sale Platform: StockX
Sale ID: 67166946-67066705
Gross Sale: 49,45 €
Net Sale: 49,45 €
Payout Received?: true
ROI: 15 %
Profit: 7,43 €
Shelf Life: 13
Brand: Adidas'''),

    ('1026181', 'https://www.notion.so/14a2a716dc4380c98617c08ca2a22b06',
     '''1026181
Size: 39
Type: EU
Buy Date: 2024-11-22
Status: Sale completed
Delivery Date: 2024-11-25
Gross Buy: 94,89 €
VAT?: true
Net Buy: 79,74 €
Supplier: BSTN
Order No.: 13001814012
Invoice Nr.: VR131890054
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-11-24
Sale Platform: StockX
Sale ID: 69702166-69601925
Gross Sale: 115,60 €
Net Sale: 115,60 €
Payout Received?: true
ROI: 38 %
Profit: 35,86 €
Shelf Life: -1
Brand: Birkenstock'''),

    ('DD1503-124', 'https://www.notion.so/14a2a716dc43800b24e1f926',
     '''DD1503-124
Size: 12
Type: US
Buy Date: 2024-11-19
Status: Sale completed
Delivery Date: 2024-11-23
Gross Buy: 58,79 €
VAT?: true
Net Buy: 49,40 €
Supplier: Solebox
Order No.: 20243723813738
Invoice Nr.: V0001018838
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-11-27
Sale Platform: StockX
Sale ID: 69776640-69676399
Gross Sale: 63,54 €
Net Sale: 63,54 €
Payout Received?: true
ROI: 24 %
Profit: 14,14 €
Shelf Life: 4
Brand: Nike'''),

    ('845053-201-v1', 'https://www.notion.so/13d2a716dc4380648f42c6d228c2aa54',
     '''845053-201
Size: 10.5
Type: US
Buy Date: 2024-11-07
Status: Sale completed
Delivery Date: 2024-11-11
Gross Buy: 78,74 €
VAT?: true
Net Buy: 66,17 €
Supplier: BSTN
Order No.: 12001654642
Invoice Nr.: VR131861321
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-11-12
Sale Platform: StockX
Sale ID: 69319296-69219055
Gross Sale: 67,59 €
Net Sale: 67,59 €
Payout Received?: true
ROI: 2 %
Profit: 1,42 €
Shelf Life: 1
Brand: Nike'''),

    ('DC0774-001', 'https://www.notion.so/15e2a716dc4380678819fa5f44421540',
     '''DC0774-001
Size: 5.5
Type: US
Buy Date: 2024-12-08
Status: Sale completed
Delivery Date: 2024-12-11
Gross Buy: 54,59 €
VAT?: true
Net Buy: 45,87 €
Supplier: Solebox
Order No.: 20243723845281
Invoice Nr.: V0001040510
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-12-19
Sale Platform: StockX
Sale ID: 70993693-70893452
Gross Sale: 59,29 €
Net Sale: 59,29 €
Payout Received?: true
ROI: 25 %
Profit: 13,42 €
Shelf Life: 8
Brand: Jordan'''),

    ('845053-201-v2', 'https://www.notion.so/14f2a716dc4380dfaac3c699f9bd0be3',
     '''845053-201
Size: 9
Type: US
Buy Date: 2024-11-22
Status: Sale completed
Delivery Date: 2024-11-25
Gross Buy: 76,64 €
VAT?: true
Net Buy: 64,40 €
Supplier: BSTN
Order No.: 13001814012
Invoice Nr.: VR131890054
Email: g0tchi@turnbeutel-vergesser.com
Sale Date: 2024-11-28
Sale Platform: StockX
Sale ID: 69853555-69753314
Gross Sale: 69,85 €
Net Sale: 69,85 €
Payout Received?: true
ROI: 7 %
Profit: 5,45 €
Shelf Life: 3
Brand: Nike'''),
]


async def main():
    """Main execution"""
    dry_run = '--dry-run' in sys.argv

    print("=" * 80)
    print("NOTION -> POSTGRESQL BULK SYNC (SAMPLE)")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE SYNC'}")
    print(f"Sales loaded: {len(NOTION_SALES_RAW)}")
    print("=" * 80)
    print()

    # Parse sales
    sales = []
    for title, url, highlight in NOTION_SALES_RAW:
        props = parse_sale_from_highlight(highlight, title, url)
        if props:
            sales.append({'url': url, 'properties': props})

    print(f"Parsed {len(sales)} valid StockX sales")
    print()

    # Initialize service
    service = NotionPostgresSyncService(dry_run=dry_run)

    try:
        await service.initialize()

        # Get session
        if not dry_run:
            session = await service.db_manager.get_session().__aenter__()
        else:
            session = None

        # Process
        for i, sale in enumerate(sales, 1):
            sale_data = service.parse_notion_properties(sale['properties'], sale['url'])

            if not sale_data:
                logger.warning(f"Invalid sale data: {sale['properties'].get('SKU')}")
                service.stats['skipped_invalid'] += 1
                continue

            service.stats['total_found'] += 1

            # Check if synced
            if not dry_run:
                if await service.check_if_synced(session, sale_data['sale_id']):
                    logger.info(f"Already synced: {sale_data['sale_id']}")
                    service.stats['already_synced'] += 1
                    continue

            # Sync
            if dry_run:
                logger.info(f"[DRY RUN] {sale_data['sku']}: {sale_data['sale_id']}")
                service.stats['newly_synced'] += 1
            else:
                success = await service.sync_sale(session, sale_data)
                if success:
                    await session.commit()
                    logger.info(f"Synced: {sale_data['sku']}")

        # Summary
        print()
        service.print_summary()

        if not dry_run and service.stats['newly_synced'] > 0:
            print()
            print("Verify in database:")
            print("  SELECT * FROM transactions.orders ORDER BY created_at DESC LIMIT 5;")

    finally:
        if not dry_run and 'session' in locals() and session:
            await session.__aexit__(None, None, None)
        await service.close()


if __name__ == '__main__':
    asyncio.run(main())