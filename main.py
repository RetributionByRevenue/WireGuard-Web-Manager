import os
import subprocess
from flask import Flask, render_template_string, request, redirect, url_for
import qrcode
import base64
from io import BytesIO

app = Flask(__name__)

CONFIG_PATH = '/etc/wireguard/wg0.conf'

def generate_keys():
    private_key = subprocess.check_output(["wg", "genkey"]).decode("utf-8").strip()
    public_key = subprocess.check_output(["wg", "pubkey"], input=private_key.encode()).decode("utf-8").strip()
    return private_key, public_key

def parse_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, 'r') as f:
        return f.read()

def write_config(content):
    with open(CONFIG_PATH, 'w') as f:
        f.write(content)

def generate_config():
    private_key, public_key = generate_keys()
    config = f"""[Interface]
# PrivateKey = {private_key}
# PublicKey = {public_key}
Address = 11.0.0.1/24
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
PrivateKey = {private_key}
ListenPort = 51820
"""
    write_config(config)
    return config

def parse_peers(config):
    peers = []
    current_peer = None
    for line in config.split('\n'):
        if line.startswith('[Peer'):
            if current_peer:
                peers.append(current_peer)
            current_peer = {'name': line.strip('[]')}
        elif current_peer and '=' in line:
            key, value = line.split('=', 1)
            current_peer[key.strip()] = value.strip()
    if current_peer:
        peers.append(current_peer)
    return [p for p in peers if '# PrivateKey' in p and '# PublicKey' in p]

def get_server_info(config):
    lines = config.split('\n')
    server_info = {}
    interface_section = False
    for line in lines:
        if line.strip() == '[Interface]':
            interface_section = True
        elif line.startswith('['):
            interface_section = False
        elif interface_section:
            if line.startswith('Address'):
                server_info['Address'] = line.split('=')[1].strip().split('/')[0]
            elif line.startswith('ListenPort'):
                server_info['ListenPort'] = line.split('=')[1].strip()
            elif line.startswith('# PublicKey'):
                server_info['PublicKey'] = line.split('=')[1].strip()
    return server_info

@app.route('/')
def index():
    config = parse_config()
    generate_button = config is None
    html = """
    <h1>WireGuard Configuration</h1>
    <nav>
        <ul>
            <li><a href="/">Server Config</a></li>
            <li><a href="/peers">Peers</a></li>
        </ul>
    </nav>
    {% if generate_button %}
        <form action="/generate_config" method="post">
            <input type="submit" value="Generate WireGuard Config">
        </form>
    {% else %}
        <h2>Server Configuration</h2>
        <pre>{{ config_content }}</pre>
        <!-- New Button to Make New Server Config -->
        <form action="/generate_new_config" method="post">
            <input type="submit" value="Make New Server Config">
        </form>
    {% endif %}
    """
    return render_template_string(html, generate_button=generate_button, config_content=config)

@app.route('/generate_new_config', methods=['POST'])
def generate_new_config():
    # Logic to generate a new server configuration
    generate_config()  # Reuse the generate_config() function or create a new one
    return redirect(url_for('index'))

@app.route('/generate_config', methods=['POST'])
def generate_config_route():
    generate_config()
    return redirect(url_for('index'))

@app.route('/peers')
def peers():
    config = parse_config()
    if config is None:
        return redirect(url_for('index'))
    
    peers = parse_peers(config)
    html = """
    <h1>WireGuard Peers</h1>
    <nav>
        <ul>
            <li><a href="/">Server Config</a></li>
            <li><a href="/peers">Peers</a></li>
        </ul>
    </nav>
<script>
    function deletePeer(privateKey) {
        if (confirm('Are you sure you want to delete the peer with Private Key: ' + privateKey + '?')) {
            fetch('/delete_peer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'peer_private_key': privateKey
                })
            })
            .then(response => {
                if (response.ok) {
                    window.location.reload();  // Reload the page to reflect changes
                } else {
                    alert('Failed to delete peer.');
                }
            })
            .catch(error => console.error('Error:', error));
        }
    }

</script>


    {% if peers %}
        <table border="1">
            <tr>
                <th>Name</th>
                <th>Public Key</th>
                <th>Allowed IPs</th>
                <th>Actions</th>
            </tr>
            {% for peer in peers %}
                <tr>
                    <td>{{ peer['name'] }}</td>  <!-- Display the name as Peer1, Peer2, etc. -->
                    <td>{{ peer['# PublicKey'] }}</td>
                    <td>{{ peer.get('AllowedIPs', 'N/A') }}</td>
<td>
    <form action="/export_peer" method="post" style="display:inline;">
        <input type="hidden" name="peer_name" value="{{ peer['name'] }}">
        <input type="submit" value="Peer Export">
    </form>
    <button id="{{ peer['# PrivateKey'] }}" onclick="deletePeer(this.id)">Delete Peer</button>
</td>
                </tr>
            {% endfor %}
        </table>
    {% endif %}
    <form action="/add_peer" method="post">
        <input type="submit" value="Add Peer">
    </form>
    """
    return render_template_string(html, peers=peers)

@app.route('/add_peer', methods=['POST'])
def add_peer():
    config = parse_config()
    if config is None:
        return redirect(url_for('index'))
    
    private_key, public_key = generate_keys()
    
    # Calculate the next peer number based on existing peers
    peers = parse_peers(config)
    peer_number = len(peers) + 1  # Get the current number of peers and add 1 for the new one
    
    new_peer = f"""
[Peer]
# PrivateKey = {private_key}
# PublicKey = {public_key}
PublicKey = {public_key}
AllowedIPs = 11.0.0.{peer_number + 1}/32
"""
    
    config += new_peer
    write_config(config)

    return redirect(url_for('peers'))


@app.route('/export_peer', methods=['POST'])
def export_peer():
    config = parse_config()
    peer_name = request.form['peer_name']
    peers = parse_peers(config)
    server_info = get_server_info(config)
    
    peer = next((p for p in peers if p['name'] == peer_name), None)
    
    if peer is None:
        return "Peer not found", 404

    # Set initial DNS and Endpoint values
    dns_value = "1.1.1.1"  # Default DNS value (can be modified)
    endpoint_value = f"{server_info['Address']}:{server_info['ListenPort']}"  # Default Endpoint

    peer_config = f"""[Interface]
PrivateKey = {peer['# PrivateKey']}
Address = {peer['AllowedIPs']}
DNS = {dns_value}

[Peer]
PublicKey = {server_info['PublicKey'] + '='}
Endpoint = {endpoint_value}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(peer_config)
    qr.make(fit=True)
    
    img = qr.make_image(fill='black', back_color='white')
    
    # Convert the QR code image to Base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    html = """
<h1>Peer Configuration Export</h1>
<nav>
    <ul>
        <li><a href="/">Server Config</a></li>
        <li><a href="/peers">Peers</a></li>
    </ul>
</nav>
<h2>Configuration for {{ peer_name }}</h2>
<form id="dns-form" onsubmit="return updateDns(event)">
    <label for="dns">DNS:</label>
    <input type="text" id="dns" name="dns" placeholder="1.1.1.1" value="{{ dns }}" style="color: grey;">
    <button type="submit">Update DNS</button>
</form>
<form id="endpoint-form" onsubmit="return updateEndpoint(event)">
    <label for="endpoint">Endpoint:</label>
    <input type="text" id="endpoint" name="endpoint" placeholder="11.0.0.1:51820" value="{{ endpoint }}" style="color: grey;">
    <button type="submit">Update Endpoint</button>
</form>
<table border="1">
    <tr>
        <th>QR Code</th>
        <th>Peer Configuration</th>
    </tr>
    <tr>
        <td id="qr"><img src="data:image/png;base64,{{ qr_code }}" width=250px height=250px alt="QR Code" /></td>
        <td id="config"><pre>{{ peer_config }}</pre></td>
    </tr>
</table>

<a href="/peers">Back to Peers</a>

<script>
    async function updateDns(event) {
        console.log(event)
        event.preventDefault();  // Prevent the form from submitting normally
        const dnsInput = document.getElementById('dns');
        const dnsValue = dnsInput.value;

        // Capture the current configuration text from the DOM
        const currentConfig = document.getElementById('config').innerText;

        // Send the request to update DNS
        const response = await fetch('/update_dns', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                peer_name: '{{ peer_name }}',  // Send the current peer name
                dns: dnsValue,
                current_config: currentConfig  // Send the current configuration text
            })
        });

        if (response.ok) {
            const data = await response.json();
            // Update the QR code and peer configuration in the DOM
            document.getElementById('qr').innerHTML = `<img src="data:image/png;base64,${data.qr_code}" width="250px" height="250px" alt="QR Code" />`;
            document.getElementById('config').innerText = data.peer_config;
        } else {
            console.error('Error updating DNS:', await response.text());
        }
    }
function updateEndpoint(event) {
    event.preventDefault(); // Prevent default form submission

    const endpoint = document.getElementById('endpoint').value;
    const currentConfig = document.getElementById('config').innerText; // Get the current config

    // Create the data object to send in the request
    const data = {
        endpoint: endpoint,
        current_config: currentConfig
    };

    // Send the POST request to update the endpoint
    fetch('/update_endpoint', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        // Assuming the result contains the updated QR code and configuration
        document.getElementById('qr').innerHTML = `<img src="data:image/png;base64,${result.qr_code}" width=250px height=250px alt="QR Code" />`;
        document.getElementById('config').innerText = result.peer_config; // Update the configuration text
    })
    .catch(error => {
        console.error('Error:', error);
    });

    return false; // Prevent the default form submission
}

</script>

    """
    
    return render_template_string(html, peer_name=peer_name, qr_code=qr_code_base64, peer_config=peer_config, dns_value=dns_value, endpoint_value=endpoint_value)


@app.route('/delete_peer', methods=['POST'])
def delete_peer():
    print("clicked")
    config = parse_config()
    peer_private_key = request.form['peer_private_key']
    
    if config is None:
        return redirect(url_for('index'))
    
    # Split config into lines for manipulation
    config_lines = config.split('\n')

    # Find the index of the PrivateKey line
    priv_index = None
    for i, line in enumerate(config_lines):
        if line.startswith(f'# PrivateKey = {peer_private_key}'):
            priv_index = i
            break
    print(priv_index)
    for i in range(priv_index, 0, -1):
        if "[Peer]" in str(config_lines[i]):
            peer_index=i
            break

    print(peer_index)
    for i in range(priv_index, len(config_lines)-1):
        if "AllowedIPs" in str(config_lines[i]):
            end_index=i+1
            break
    print(end_index)

    # Check boundaries and remove lines for the peer
    #indices_to_remove = config_lines[peer_index:end_index]
    del config_lines[peer_index-1:end_index]

    # Write the updated config
    write_config("\n".join(config_lines))

    
    return redirect(url_for('peers'))


@app.route('/update_dns', methods=['POST'])
def update_dns():
    data = request.get_json()
    new_dns = data['dns']
    current_config = data['current_config'].split('\n')  # Capture current configuration
    print(current_config,"here 1")
    for i in range(0,len(current_config)):
        if "DNS" in str(current_config[i]):
            current_config[i] = f'DNS = {new_dns}'
    print(current_config,"here 2")
    current_config="\n".join(current_config)

    


    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(current_config)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    # Convert the QR code image to Base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return {'qr_code': qr_code_base64, 'peer_config': current_config}, 200

@app.route('/update_endpoint', methods=['POST'])
def update_endpoint():
    data = request.get_json()
    new_endpoint = data['endpoint']
    current_config = data['current_config'].split('\n')  # Capture current configuration

    print(current_config, "here 1")
    for i in range(len(current_config)):
        if "Endpoint" in current_config[i]:
            current_config[i] = f'Endpoint = {new_endpoint}'
    
    print(current_config, "here 2")
    current_config = "\n".join(current_config)

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(current_config)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    # Convert the QR code image to Base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return {'qr_code': qr_code_base64, 'peer_config': current_config}, 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5080, debug=True)
