import os, sys
import os.path, time
import csv
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import timedelta
from datetime import datetime, timezone
from scapy.all import rdpcap
from pprint import pprint
from scapy.layers.inet import ICMP
from scapy.layers.l2 import ARP
import scapy.contrib.igmp
import time

def print_dic(ip_to_ip_data):
    # Print a portion of the dictionary
    for i, ((src_ip, dst_ip), time_series_data) in enumerate(ip_to_ip_data.items()):
        print(f"Source IP: {src_ip}, Destination IP: {dst_ip}")
        for timestamp, sizes in sorted(time_series_data.items())[:5]:  # First 5 timestamps
            print(f"  {timestamp}: {sizes}")
        if i >= 10:  # Stop after showing 10 IP pairs
            break

def process_pcap(pcap_file, output_dir):
    packets = rdpcap(pcap_file)

    # Data structure to store time series data
    # ip_to_ip_data = defaultdict(lambda: {"incoming": [], "outgoing": []})
    ip_to_ip_data = defaultdict(lambda: defaultdict(lambda: {
        'L2_IP_ingoing':    0, 'L2_IP_outgoing':    0,
        'L2_ARP_ingoing':   0, 'L2_ARP_outgoing':   0,
        'L2_ICMP_ingoing':  0, 'L2_ICMP_outgoing':  0,
        'L2_IGMP_ingoing':  0, 'L2_IGMP_outgoing':  0,
        'L2_Other_ingoing': 0, 'L2_Other_outgoing': 0,
        'L2_Total_ingoing': 0, 'L2_Total_outgoing': 0
    }))

    for packet in packets:
        #fromtimestamp(float(packet.time), timezone.utc)
        timestamp = packet.time
        pkt_time = datetime.fromtimestamp(int(timestamp), timezone.utc)
        if packet.haslayer('IP'):
            src_ip = packet['IP'].src
            dst_ip = packet['IP'].dst
            pkt_size = len(packet)  # Packet size in bytes      

            # Update total traffic size for src->dst
            ip_to_ip_data[(src_ip, dst_ip)][pkt_time]['L2_IP_ingoing'] += pkt_size
            # Update total traffic size for dst->src
            ip_to_ip_data[(dst_ip, src_ip)][pkt_time]['L2_IP_outgoing'] += pkt_size

        elif packet.haslayer(ARP):
            pkt_size = len(packet)  # Packet size in bytes
            src_mac = packet[ARP].hwsrc  # Source MAC
            dst_mac = packet[ARP].hwdst  # Destination MAC

            # Update total traffic size for src->dst
            ip_to_ip_data[(src_mac, dst_mac)][pkt_time]['L2_ARP_ingoing'] += pkt_size
            # Update total traffic size for dst->src
            ip_to_ip_data[(dst_mac, src_mac)][pkt_time]['L2_ARP_outgoing'] += pkt_size

        elif packet.haslayer(ICMP):
            src_ip = packet['IP'].src
            dst_ip = packet['IP'].dst
            pkt_size = len(packet)  # Packet size in bytes

            # Update total traffic size for src->dst
            ip_to_ip_data[(src_ip, dst_ip)][pkt_time]['L2_ICMP_ingoing'] += pkt_size
            # Update total traffic size for dst->src
            ip_to_ip_data[(dst_ip, src_ip)][pkt_time]['L2_ICMP_outgoing'] += pkt_size

        elif packet.haslayer(IGMP):
            src_ip = packet['IP'].src
            dst_ip = packet['IP'].dst
            pkt_size = len(packet)  # Packet size in bytes

            # Update total traffic size for src->dst
            ip_to_ip_data[(src_ip, dst_ip)][pkt_time]['L2_IGMP_ingoing'] += pkt_size
            # Update total traffic size for dst->src
            ip_to_ip_data[(dst_ip, src_ip)][pkt_time]['L2_IGMP_outgoing'] += pkt_size

        else:
            # Update total traffic size for src->dst
            ip_to_ip_data[(src_ip, dst_ip)][pkt_time]['L2_Other_ingoing'] += pkt_size
            # Update total traffic size for dst->src
            ip_to_ip_data[(dst_ip, src_ip)][pkt_time]['L2_Other_outgoing'] += pkt_size
        
        ip_to_ip_data[(src_ip, dst_ip)][pkt_time]['L2_Total_ingoing'] += pkt_size
        ip_to_ip_data[(dst_ip, src_ip)][pkt_time]['L2_Total_outgoing'] += pkt_size

        # print_dic(ip_to_ip_data)

    for (src_ip, dst_ip), time_series_data in ip_to_ip_data.items():
        print(src_ip, dst_ip)
        #all_timestamps = sorted(datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") if isinstance(ts, str) else ts for ts in time_series_data.keys())
        all_timestamps = sorted(time_series_data.keys())
        all_timestamp_key = list(time_series_data.keys())
        if not all_timestamps:
            continue
        
        start_time = all_timestamp_key[0]
        end_time = all_timestamp_key[-1]
        # Fill missing timestamps with zeros
        filled_data = {}
        current_time = start_time
        current_second = 0
        while current_time <= end_time:
            if current_time in time_series_data:
                filled_data[current_time] = time_series_data[current_time]
            else:
                # Add zero values for missing timestamps
                filled_data[current_time] = {
                    'L2_IP_ingoing':    0, 'L2_IP_outgoing':    0,
                    'L2_ARP_ingoing':   0, 'L2_ARP_outgoing':   0,
                    'L2_ICMP_ingoing':  0, 'L2_ICMP_outgoing':  0,
                    'L2_IGMP_ingoing':  0, 'L2_IGMP_outgoing':  0,
                    'L2_Other_ingoing': 0, 'L2_Other_outgoing': 0,
                    'L2_Total_ingoing': 0, 'L2_Total_outgoing': 0
                }
            current_time += timedelta(seconds=1)
 
            csv_filename = f"{output_dir}/{src_ip}_to_{dst_ip}.csv"
            with open(csv_filename, mode='w', newline='') as csv_file:
                fieldnames = [
                    'timestamp', 'source_ip', 'destination_ip', 'seconds',
                    'L2_IP_ingoing',    'L2_IP_outgoing',
                    'L2_ARP_ingoing',   'L2_ARP_outgoing',
                    'L2_ICMP_ingoing',  'L2_ICMP_outgoing',
                    'L2_IGMP_ingoing',  'L2_IGMP_outgoing',
                    'L2_Other_ingoing', 'L2_Other_outgoing',
                    'L2_Total_ingoing', 'L2_Total_outgoing'
                ]
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()          
                for timestamp, sizes in sorted(filled_data.items()):
                    row = {'timestamp': timestamp, 'source_ip': src_ip, 'destination_ip': dst_ip, 'seconds': current_second}
                    row.update(sizes)
                    writer.writerow(row)
                    current_second += 1
    print(f"Processed and exported data to {output_dir}")


def main(in_dir, out_dir):
    for filename in os.listdir(in_dir):
        if filename.endswith(".pcap"):
            print(f"PCAP File:\t{filename}")
            packet_data = []
            pcap_file_path = os.path.join(in_dir, filename)
            process_pcap(pcap_file_path, out_dir)

def run(in_dir, out_dir, IS_MALWARE):
    if not os.path.exists(in_dir):
        print(f"Directory: '{in_dir}' does not exist.")
        exit()
    print(f"\n\nPCAP Directory:\t\t{in_dir}")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    print(f"CSV Files will save:\t{out_dir}")
    print(f"DATASET is malware:\t{IS_MALWARE}\n\n")
    main(in_dir, out_dir)

if __name__ == "__main__":
  print("[" + __file__ + "]'s last modified: %s" % time.ctime(os.path.getmtime(__file__)))
  # Check if a parameter is provided
  if len(sys.argv) == 4 :
    in_dir = sys.argv[1]
    if not os.path.exists(in_dir):
        print(f"Directory: '{in_dir}' does not exist.")
        exit()         
    print(f"\n\nPCAP Directory:\t\t{in_dir}")

    out_dir = sys.argv[2]
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    print(f"CSV Files will save:\t{out_dir}")   
    
    IS_MALWARE = sys.argv[3]    
    print(f"DATASET is malware:\t{IS_MALWARE}\n\n")
    main(in_dir, out_dir)
  else:
    print("No input directory and output directory provided.")
