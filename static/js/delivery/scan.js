let scanActive = false;

// Start scanning
function startRFIDScan() {
    fetch('/start_scan', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'scan_started') {
                scanActive = true;
                document.getElementById('startScanBtn').style.display = 'none';
                document.getElementById('stopScanBtn').style.display = 'inline-block';
                console.log("🔍 RFID scanning started");
                pollRFID();
            }
        })
        .catch(err => console.error(err));
}

// Stop scanning
function stopRFIDScan() {
    scanActive = false;
    document.getElementById('startScanBtn').style.display = 'inline-block';
    document.getElementById('stopScanBtn').style.display = 'none';
    console.log("🛑 RFID scanning stopped");
}

// Poll the server for scan status
function pollRFID() {
    if (!scanActive) return;

    fetch('/esp/scan_status')
        .then(res => res.json())
        .then(data => {
            if (data.scan === true) {
                // Continue polling while scan is active
                setTimeout(pollRFID, 1000);
            } else {
                // Scan finished → fetch last RFID
                fetchLastRFID();
            }
        })
        .catch(err => console.error(err));
}

// Fetch last scanned RFID
function fetchLastRFID() {
    fetch('/rfid_last')
        .then(res => res.json())
        .then(rfidData => {
            if (rfidData && rfidData.rfid) {
                console.log("📦 RFID:", rfidData.rfid);
                fillRFID(rfidData.rfid);
            }
        })
        .catch(err => console.error(err));
}

// Fill RFID input and fetch product info
function fillRFID(rfid) {
    const rfidInput = document.getElementById('rfidTag');
    rfidInput.value = rfid;

    // POST request to update order & inventory
    fetch(`/delivery/by_rfid/${rfid}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Show success message
                alert(`✅ ${data.message}`);
                console.log(data);

                // Refresh the entire page
                window.location.reload();
            } else {
                alert(`ℹ️ ${data.message}`);
            }
        })
        .catch(err => console.error("Error processing RFID scan:", err));

    // Stop scanning after successful read
    stopRFIDScan();
}



// Array to temporarily store products before saving
let productsToAdd = [];
document.addEventListener("DOMContentLoaded", function () {
    fetchInventory();
});

function fetchInventory() {
    fetch('/my-inventory-data')  // We'll create a Flask route returning JSON
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('scannedProductsBody');
            tbody.innerHTML = ''; // clear existing rows

            if (!data.inventory || data.inventory.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No products found in inventory</td></tr>`;
                return;
            }

            data.inventory.forEach(product => {
                const row = document.createElement('tr');

                row.innerHTML = `
                    <td>${product.rfid_tag || ''}</td>
                    <td>${product.name || ''}</td>
                    <td>${product.product_id || ''}</td>
                    <td>${product.category || ''}</td>
                    <td>${product.stock || 0}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="removeProduct(${product.product_id})">
                            <i class="fas fa-trash"></i> Remove
                        </button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        })
        .catch(err => console.error("Error fetching inventory:", err));
}

// Add a product to the temporary list
function addProduct() {
    const rfid = document.getElementById('rfidTag').value.trim();
    const id = document.getElementById('productId').value.trim();
    const name = document.getElementById('productName').value.trim();
    const sku = document.getElementById('productSKU').value.trim();
    const quantity = parseInt(document.getElementById('quantity').value);
    const category = document.getElementById('category').value;

    if (!rfid || !name || !id || !category || quantity < 1) {
        alert("❌ Please fill all fields correctly!");
        return;
    }

    // Add to local array
    productsToAdd.push({
        rfid: rfid,
        name: name,
        product_id: id, 
        stock: quantity,
        category: category
    });

    console.log("Product added to list:", productsToAdd);

    // Clear form for next entry
    document.getElementById('rfidTag').value = '';
    document.getElementById('productId').value = '';
    document.getElementById('productName').value = '';
    document.getElementById('productSKU').value = '';
    document.getElementById('quantity').value = 1;
    document.getElementById('category').value = '';

    alert("✅ Product added to list. Click 'Save All' to save to inventory.");
}

// Save all products in the list to the seller's inventory
function saveAllProducts() {
    if (productsToAdd.length === 0) {
        alert("❌ No products to save!");
        return;
    }

    productsToAdd.forEach(product => {
        fetch('/add-product', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: product.product_id,
                stock: product.stock,
                price: null // or add a price field in the form if needed
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                console.log(`✅ ${product.name} saved:`, data.message);
                fetchInventory()
            } else {
                console.error(`❌ Error saving ${product.name}:`, data.message);
            }
        })
        .catch(err => {
            console.error(`❌ Server error for ${product.name}:`, err);
        });
    });

    // Clear temporary list
    productsToAdd = [];
    alert("✅ All products have been saved to your inventory!");
}





async function removeProduct(productId) {
  try {
    const response = await fetch(`http://127.0.0.1:5050/remove-product/${productId}`, {
      method: "DELETE"
    });
    const result = await response.json();
    console.log(result);
    fetchInventory();
  } catch (err) {
    console.error("Error removing product:", err);
  }
}
