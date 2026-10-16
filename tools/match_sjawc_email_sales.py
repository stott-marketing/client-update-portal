"""Match de-identified Boulevard client sales to GHL email keys.

Only aggregate results belong in the public report. Row-level audit stays private.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
APPOINTMENT_TAGS = {'new_appointment_zap', 'new_appointment_staff_zap', 'client_updated_zap'}

def email_key(value):
    return str(value or '').strip().casefold()

def amount(value):
    if value is None or str(value).strip() == '':
        raise ValueError('Missing sale amount; cannot treat missing data as zero')
    return Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

def source_tags(tags, appointment_tags_are_google=False):
    sources = set()
    for tag in tags:
        if tag in {'google', 'google ads', 'google_ads', 'google_ads_zap'}:
            sources.add('google_ads')
        if appointment_tags_are_google and tag in APPOINTMENT_TAGS:
            sources.add('google_ads')
        if 'facebook' in tag or 'instagram' in tag or tag.startswith('fb -') or tag == 'collagen fb lead':
            sources.add('meta')
        if tag in {'ageless', 'agelessrackcard'}:
            sources.add('ageless')
        if 'entitymed' in tag:
            sources.add('entitymed')
        if tag in {'website_embed', 'contact form submitted'}:
            sources.add('website_contact')
    return sources

def build_match(sales, contacts, appointment_tags_are_google=False):
    lookup = defaultdict(list)
    for row in contacts:
        key = email_key(row.get('Email'))
        if key:
            lookup[key].append(row)
    buckets = defaultdict(lambda: {'sales_rows': 0, 'positive_sales_rows': 0, 'sales_amount': Decimal('0')})
    reasons = defaultdict(lambda: {'sales_rows': 0, 'sales_amount': Decimal('0')})
    audit = []
    seen = set()
    identity_count = 0
    identity_total = Decimal('0')
    client_types = defaultdict(lambda: {'client_rows': 0, 'sales_amount': Decimal('0')})
    total = Decimal('0')
    order_count = 0
    for row_number, row in enumerate(sales, 2):
        key = email_key(row.get('Client email'))
        if key in seen and key:
            raise ValueError('Duplicate client key in sales export; review grain before counting')
        seen.add(key)
        value = amount(row.get('Sale amount'))
        total += value
        client_type = row.get('Client type') or 'Not specified'
        client_types[client_type]['client_rows'] += 1
        client_types[client_type]['sales_amount'] += value
        order_count += int(row.get('Order count') or 0)
        matches = lookup.get(key, []) if key else []
        tags = set()
        source = 'unattributed'
        if len(matches) == 1:
            identity_count += 1
            identity_total += value
            tags = {t.strip().casefold() for t in matches[0].get('Tags', '').split(',') if t.strip()}
            sources = source_tags(tags, appointment_tags_are_google)
            if len(sources) == 1:
                source = next(iter(sources))
                reason = 'explicit_source_tag' if not (source == 'google_ads' and not source_tags(tags)) else 'user_confirmed_appointment_tag_mapping'
            elif len(sources) > 1:
                reason = 'multiple_marketing_sources'
            else:
                reason = 'appointment_tags_only' if tags & APPOINTMENT_TAGS else 'no_marketing_source_tag'
        elif len(matches) > 1:
            reason = 'ambiguous_email_key'
        else:
            reason = 'email_not_found' if key else 'missing_email_key'
        buckets[source]['sales_rows'] += 1
        buckets[source]['positive_sales_rows'] += int(value > 0)
        buckets[source]['sales_amount'] += value
        reasons[reason]['sales_rows'] += 1
        reasons[reason]['sales_amount'] += value
        audit.append({'sales_sheet_row': row_number, 'email_key': key, 'sale_amount': str(value), 'contact_matches': len(matches), 'source_bucket': source, 'match_reason': reason, 'matched_tags': ', '.join(sorted(tags)), 'client_type': client_type, 'appointment_count': row.get('Appointment count'), 'order_count': row.get('Order count'), 'staff_requested_percent': row.get('Staff requested %'), 'pre_booked_percent': row.get('Pre-booked %'), 'self_booked_percent': row.get('Self-booked %')})
    for key in ['google_ads', 'meta', 'ageless', 'entitymed', 'website_contact', 'unattributed']:
        buckets[key]
    assigned = total - buckets['unattributed']['sales_amount']
    assert sum(b['sales_amount'] for b in buckets.values()) == total
    assert sum(b['sales_rows'] for b in buckets.values()) == len(sales)
    def serialize(groups):
        return {k: {field: float(value) if isinstance(value, Decimal) else value for field, value in data.items()} for k, data in groups.items()}
    summary = {'metrics': {'sales_amount': float(total), 'tag_matched_sales_amount': float(assigned), 'source_unknown_sales_amount': float(total-assigned), 'attribution_coverage': float(assigned/total) if total else None, 'sales_rows': len(sales), 'matched_sales_rows': identity_count, 'identity_matched_sales_amount': float(identity_total), 'order_count': order_count}, 'client_types': serialize(client_types), 'channels': serialize(buckets), 'match_reasons': serialize(reasons), 'checks': {'channel_total_reconciles': True, 'sales_rows_assigned_once': True, 'duplicate_contact_keys': sum(len(v)>1 for v in lookup.values()), 'negative_sales_rows': sum(amount(r.get('Sale amount'))<0 for r in sales), 'zero_sales_rows': sum(amount(r.get('Sale amount'))==0 for r in sales)}}
    return summary, audit

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sales', type=Path, required=True)
    parser.add_argument('--contacts', type=Path, required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--appointment-tags-are-google', action='store_true')
    parser.add_argument('--amount-basis', choices=['reported_sales', 'gross_sales', 'net_sales'], default='reported_sales')
    parser.add_argument('--output', type=Path, default=ROOT/'data/sjawc/revenue_attribution.json')
    parser.add_argument('--audit', type=Path, default=ROOT/'output/private/sjawc_email_sales_match_20261016.csv')
    args = parser.parse_args()
    with args.contacts.open(encoding='utf-8-sig', newline='') as handle:
        contacts = list(csv.DictReader(handle))
    workbook = load_workbook(args.sales, read_only=True, data_only=True)
    rows = workbook.active.iter_rows(values_only=True)
    headers = list(next(rows))
    sales = [dict(zip(headers, row)) for row in rows if any(value is not None for value in row)]
    summary, audit = build_match(sales, contacts, args.appointment_tags_are_google)
    summary.update({'source': args.sales.name, 'contacts_source': args.contacts.name, 'updated_at': '2026-10-16', 'scope': 'sales for user-confirmed export period', 'period': {'start': args.start, 'end': args.end, 'inclusive_days': (date.fromisoformat(args.end)-date.fromisoformat(args.start)).days+1}, 'method': 'Exact case-insensitive email-key match only. Duplicate contact keys remain unresolved. One explicit marketing source is required; multiple sources stay unattributed. Generic appointment tags are source-unknown unless expressly confirmed as Google-only by the user. Tags show association, not proof a campaign caused a sale.', 'appointment_tags_are_google': args.appointment_tags_are_google, 'amount_basis': args.amount_basis, 'amount_definition': 'Net of discounts/refunds as confirmed by user' if args.amount_basis == 'net_sales' else 'Gross sales before discounts/refunds, excluding sales tax; not net revenue or cash collected', 'date_limitation': 'Client-level export contains no transaction dates; its supplied period cannot be filtered to a different window.', 'input_sha256': {args.sales.name: hashlib.sha256(args.sales.read_bytes()).hexdigest(), args.contacts.name: hashlib.sha256(args.contacts.read_bytes()).hexdigest()}})
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    with args.audit.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit[0]))
        writer.writeheader(); writer.writerows(audit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
