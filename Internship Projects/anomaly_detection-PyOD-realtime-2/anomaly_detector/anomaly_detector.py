import time
import requests
import numpy as np
import pandas as pd
from pyod.models.iforest import IForest
from prometheus_client import start_http_server, Gauge

# Define Prometheus metrics
anomaly_gauge = Gauge('cpu_anomalies', 'Anomaly scores for CPU metrics')
cpu_usage_gauge = Gauge('cpu_usage', 'CPU usage')

def fetch_metrics():
    try:
        response = requests.get('http://prometheus:9090/api/v1/query', params={'query': 'rate(node_cpu_seconds_total[1m])'})
        response.raise_for_status()  # Raise an exception for HTTP errors
        results = response.json()['data']['result']
        metrics = []
        for result in results:
            if 'values' in result:
                for value in result['values']:
                    metrics.append([float(value[0]), float(value[1])])
            elif 'value' in result:
                metrics.append([float(result['value'][0]), float(result['value'][1])])
        return pd.DataFrame(metrics, columns=['timestamp', 'value'])
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return pd.DataFrame(columns=['timestamp', 'value'])

def detect_anomalies(data):
    model = IForest(contamination=0.1)
    model.fit(data)
    return model.decision_function(data)

def main():
    start_http_server(8000)  # Start Prometheus custom exporter server
    while True:
        data = fetch_metrics()
        if not data.empty:
            data['value'] = data['value'].astype(float)
            anomalies = detect_anomalies(data[['value']])
            latest_cpu_usage = data['value'].iloc[-1]  # Get the latest CPU usage value
            latest_anomaly_score = anomalies[-1]  # Get the latest anomaly score
            cpu_usage_gauge.set(latest_cpu_usage)
            anomaly_gauge.set(latest_anomaly_score)
        time.sleep(15)

if __name__ == "__main__":
    main()
