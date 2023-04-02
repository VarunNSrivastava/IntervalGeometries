const canvas = document.getElementById('scalemakerCanvas');
const ctx = canvas.getContext('2d');

// Set canvas dimensions
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

// Define global variables and constants
const numberOfBars = 12;
const barWidth = canvas.width / numberOfBars;

let mode = 'play'; // play, line, subdivide
let distribution = 'linear'; // linear, log
let isMouseDown = false;
let startPoint = null;
let lines = [];
let scrollPosition = 0;
let zoomLevel = 1;
const minFreq = 20;
const maxFreq = 1600;


const audioContext = new (window.AudioContext || window.webkitAudioContext)();
let oscillator = null;
const gainNode = audioContext.createGain();
gainNode.connect(audioContext.destination);


function createSineWaveCanvas() {
  const sineWaveCanvas = document.createElement('canvas');
  sineWaveCanvas.width = canvas.width / 8;
  sineWaveCanvas.height = canvas.height / 8;
  sineWaveCanvas.style.position = 'absolute';
  sineWaveCanvas.style.top = '0';
  sineWaveCanvas.style.right = '0'; // Change this from 'left' to 'right'
  sineWaveCanvas.style.zIndex = '2';
  canvas.parentElement.appendChild(sineWaveCanvas);

  return sineWaveCanvas;
}

let offsetX = 0;
let currentPlayingFrequency = null;

// sine wave plotter
const sineWaveCanvas = createSineWaveCanvas();
const sineWaveCtx = sineWaveCanvas.getContext('2d');


function animateSineWave() {
  const rate = 12;
  const period = Math.PI / 800;
  const xIncrement = period / sineWaveCanvas.width;

  offsetX += xIncrement * currentPlayingFrequency * rate;
  if (offsetX >= period) {
    offsetX -= period;
  }
  drawSineWave(currentPlayingFrequency, offsetX); // Add this line to call drawSineWave
}


// Functions
function drawSineWave(frequency, offset) {
  sineWaveCtx.clearRect(0, 0, sineWaveCanvas.width, sineWaveCanvas.height);
  if (frequency === null) {
    return;
  }

  const centerY = sineWaveCanvas.height / 2;
  const amplitude = sineWaveCanvas.height / 4;
  const period = Math.PI / 1000;
  const angularFrequency = 2 * Math.PI * frequency;
  const xIncrement = period / sineWaveCanvas.width;

  sineWaveCtx.beginPath();
  sineWaveCtx.moveTo(0, centerY);
  console.log(offsetX);

  for (let x = 0; x < sineWaveCanvas.width; x++) {
    const theta = offset + angularFrequency * (x / sineWaveCanvas.width) * period;
    const y = centerY + amplitude * Math.sin(theta);
    sineWaveCtx.lineTo(x, y);
  }

  sineWaveCtx.stroke();
}

function addLine(startX, startY, endX, endY) {
  lines.push({
    startX: startX,
    startY: startY,
    endX: endX,
    endY: endY,
  });
}


function drawBars() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = '12px Arial';
  ctx.textBaseline = 'middle';

  const barHeight = canvas.height / numberOfBars;

  for (let i = 0; i < numberOfBars; i++) {
    const y = i * barHeight;

    // Draw the horizontal line
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();

    // Draw the frequency labels for the middle bar
    if (i === Math.floor(numberOfBars / 2)) {
      const freqsToLabel = [220, 440, 880];
      freqsToLabel.forEach((freq) => {
        const x = getXPositionFromFrequency(freq);
        ctx.fillText(freq + ' Hz', x, y - 5);
      });
    }
  }
}



function switchMode(newMode) {
  mode = newMode;
}

function switchDistribution(newDistribution) {
  distribution = newDistribution;
  drawBars(); // Redraw bars with the new distribution
}


// just use math to make this and the next function
// exact inverses


// "zoom" pretty much only matters for these functions
// (and then later, lines and such)
function getFrequencyFromXPosition(x) {
  const adjustedX = (x - canvas.width / 2) * zoomLevel + canvas.width / 2 - scrollPosition;

  let frequency;
  if (distribution === 'linear') {
    frequency = minFreq + adjustedX * (maxFreq - minFreq) / canvas.width;
  } else {
    const minLogFrequency = Math.log10(minFreq);
    const maxLogFrequency = Math.log10(maxFreq);
    const logFrequency = minLogFrequency + adjustedX * (maxLogFrequency - minLogFrequency) / canvas.width;
    frequency = Math.pow(10, logFrequency);
  }

  return frequency;
}

function getXPositionFromFrequency(frequency) {
  let x;
  if (distribution === 'linear') {
    x = (frequency - minFreq) * canvas.width / (maxFreq - minFreq);
  } else {
    const minLogFrequency = Math.log10(minFreq);
    const maxLogFrequency = Math.log10(maxFreq);
    const logFrequency = Math.log10(frequency);
    x = (logFrequency - minLogFrequency) * canvas.width / (maxLogFrequency - minLogFrequency);
  }

  const adjustedX = (x - canvas.width / 2) / zoomLevel + canvas.width / 2 + scrollPosition;
  return adjustedX;
}


function drawLine(startX, startY, endX, endY) {
  ctx.beginPath();
  ctx.moveTo(startX, startY);
  ctx.lineTo(endX, endY);
  ctx.stroke();
}


function subdivideLine(line, parts) {
    //todo
}

function playFrequency(targetFrequency) {
  if (targetFrequency < minFreq || targetFrequency > maxFreq) {
    return;
  }
  const interpolationDuration = 0.05; // 50 ms interpolation duration

  if (oscillator) {
    const startFrequency = oscillator.frequency.value;
    oscillator.frequency.cancelScheduledValues(audioContext.currentTime);
    oscillator.frequency.setValueAtTime(startFrequency, audioContext.currentTime);
    oscillator.frequency.linearRampToValueAtTime(targetFrequency, audioContext.currentTime + interpolationDuration);
  } else {
    oscillator = audioContext.createOscillator();
    oscillator.frequency.setValueAtTime(targetFrequency, audioContext.currentTime);
    oscillator.connect(gainNode);

    // Fade-in effect
    gainNode.gain.setValueAtTime(0, audioContext.currentTime);
    gainNode.gain.linearRampToValueAtTime(1, audioContext.currentTime + 0.01); // 0.01 second fade-in

    oscillator.start();
  }
  currentPlayingFrequency = targetFrequency;
  // drawSineWave(targetFrequency);
}

function stopFrequency() {
  if (oscillator) {
    // Fade-out effect
    gainNode.gain.setValueAtTime(1, audioContext.currentTime);
    gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.01); // 0.01 second fade-out

    // Stop the oscillator after the fade-out is complete
    setTimeout(() => {
      oscillator.stop();
      oscillator = null;
    }, 10);
  }

}


// Event listeners

canvas.addEventListener('mousedown', (event) => {
  isMouseDown = true;
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  startPoint = {x: x, y: y};
  // Implement functionality depending on the current mode
  if (mode === 'play') {
    const frequency = getFrequencyFromXPosition(x);
    playFrequency(frequency);
  
  } else if (mode === 'line') {
    // Start drawing a line
    ctx.strokeStyle = 'red'; // Set the line color; change it as desired
    ctx.lineWidth = 2; // Set the line width; change it as desired
    drawLine(startPoint.x, startPoint.y, startPoint.x, startPoint.y);
  } else if (mode === 'subdivide') {
    // Find the nearest line and subdivide it into equal parts
    // TODO
    }
});

canvas.addEventListener('mousemove', (event) => {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  if (isMouseDown && mode === 'play') {
    // change frequency
    const frequency = getFrequencyFromXPosition(x);
    playFrequency(frequency);

  } else if (isMouseDown && mode == 'line') {
    ctx.clearRect(0, 0, canvas.width, canvas.height); // Clear the canvas
    drawBars(); // Redraw the bars
    drawLine(startPoint.x, startPoint.y, x, y);
  }
});

canvas.addEventListener('mouseup', (event) => {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  isMouseDown = false;

  if (mode === 'play') {
    // Stop playing frequency
    console.log('Stopping frequency playback');
    stopFrequency();
    currentPlayingFrequency = null;
  } else if (mode === 'line') {
    // Finish drawing the line
    addLine(startPoint.x, startPoint.y, x, y);
  }
});

// Event listener for the 'wheel' event
canvas.addEventListener('wheel', (event) => {
  event.preventDefault();

  if (event.ctrlKey) { // Zoom when the Ctrl key is pressed
    const zoomFactor = 1 + event.deltaY * -0.01; // Adjust the zoom factor based on the deltaY value
    zoomLevel *= zoomFactor;
    zoomLevel = Math.min(Math.max(zoomLevel, 0.25), 4);
  } else { // Scroll when the Ctrl key is not pressed
    scrollPosition -= 0.5 * event.deltaX;
    scrollPosition = Math.min(Math.max(scrollPosition, -canvas.width / 2 / zoomLevel), canvas.width / 2 / zoomLevel);
  }

  // Redraw the bars after adjusting the scroll position or zoom level
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawBars();
}, { passive: false });

canvas.addEventListener('gesturestart', (event) => {
  event.preventDefault();
});

canvas.addEventListener('gesturechange', (event) => {
  event.preventDefault();
  zoomLevel *= event.scale; // Adjust the zoom level based on the scale value
  zoomLevel = Math.min(Math.max(zoomLevel, 0.25), 4);

  // Redraw the bars after adjusting the zoom level
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawBars();
});

setInterval(animateSineWave, 1000 / 60);
drawBars();
