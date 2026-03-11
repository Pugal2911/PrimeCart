document.getElementById('addProductForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const res = await fetch('/admin/add-product', {
        method: 'POST',
        body: formData
    });
    const result = await res.json();
    if (result.status === 'success') {
        alert('Product added successfully!');
        location.reload();
    } else {
        alert(result.message);
    }
});


const socket = io("http://192.168.1.15:5050/"); // default namespace

const scanBtn = document.getElementById("scanRFIDBtn");
const rfidInput = document.getElementById("productRFID");


document.addEventListener("DOMContentLoaded", () => {
    const scanBtn = document.getElementById("scanRFIDBtn");
    if (scanBtn) {
        scanBtn.addEventListener("click", async () => {
            scanBtn.disabled = true;
            const rfidInput = document.getElementById("productRFID");
            if (rfidInput) rfidInput.value = "Waiting for RFID scan...";

            try {
                const res = await fetch("/start_scan", { method: "POST" });
                const data = await res.json();
                console.log("Start scan response:", data);
            } catch (err) {
                console.error("Failed to start scan:", err);
            }
        });
    }
});

socket.on("connect", () => {
  console.log("✅ Socket connected");
});

socket.on("rfid_scanned", data => {
    console.log("RFID received:", data);
    rfidInput.value = data.rfid;
    scanBtn.disabled = false;
});

socket.on("disconnect", () => {
  console.log("❌ Socket disconnected");
});
