let drawing = false;
let previousX, previousY;

function setup() {
  createCanvas(400, 300);
  background(240);
}

function mousePressed() {
  drawing = true;
  previousX = mouseX;
  previousY = mouseY;
}

function mouseReleased() {
  drawing = false;
}

function mouseDragged() {
  if (drawing) {
    fill(0);
    line(previousX, previousY, mouseX, mouseY);
    sendLineData(previousX, previousY, mouseX, mouseY);
    previousX = mouseX;
    previousY = mouseY;
  }
}

async function sendLineData(startX, startY, endX, endY) {
  const data = { start_x: startX, start_y: startY, end_x: endX, end_y: endY };
  try {
    const response = await fetch('/api/save_line', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      console.error('Failed to save line:', response.status);
    } else {
      const result = await response.json();
      console.log('Line saved:', result.message);
    }
  } catch (error) {
    console.error('Error sending data:', error);
  }
}

async function loadLines() {
  try {
    const response = await fetch('/api/get_lines');
    if (response.ok) {
      const lines = await response.json();
      lines.forEach(lineData => {
        stroke(100); // 保存された線の色
        line(lineData.start_x, lineData.start_y, lineData.end_x, lineData.end_y);
      });
    } else {
      console.error('Failed to load lines:', response.status);
    }
  } catch (error) {
    console.error('Error loading lines:', error);
  }
}

window.onload = loadLines;