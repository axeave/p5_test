class Sketch {
    constructor() {
        this.drawing = false;
        this.previousX = 0;
        this.previousY = 0;
        this.currentLinesBuffer = [];
        this.sketchId = null;
        this.p5Canvas = createCanvas(600, 400);

        let canvasElement = document.querySelector('canvas');
        let controlsDiv = document.getElementById('controls');
        if (controlsDiv && canvasElement) {
            controlsDiv.insertAdjacentElement('afterend', this.p5Canvas.canvas);
        }

        background(230);
        stroke(0);
        strokeWeight(2);

        // イベントリスナーをバインド
        this.p5Canvas.mousePressed(this.startDrawing.bind(this));
        this.p5Canvas.mouseReleased(this.endDrawing.bind(this));
    }

    async startDrawing() {
        if (mouseX > 0 && mouseX < width && mouseY > 0 && mouseY < height) {
            this.drawing = true;
            this.previousX = mouseX;
            this.previousY = mouseY;

            if (!this.sketchId) {
                const sketchResponse = await fetch('/api/create_sketch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });

                if (!sketchResponse.ok) {
                    const errorResult = await sketchResponse.json();
                    throw new Error(`スケッチの作成に失敗しました: ${errorResult.error || sketchResponse.status}`);
                }

                const sketchResult = await sketchResponse.json();
                this.sketchId = sketchResult.sketch_id;
                console.log('Sketch created with ID:', this.sketchId);
            }
        }
    }

    async endDrawing() {
        this.drawing = false;
        if (this.currentLinesBuffer.length > 0) {
            await this.saveSketch();
        }
    }

    mouseDragged() {
        if (this.drawing) {
            const currentX = mouseX;
            const currentY = mouseY;
            line(this.previousX, this.previousY, currentX, currentY);
            this.currentLinesBuffer.push({
                start_x: this.previousX,
                start_y: this.previousY,
                end_x: currentX,
                end_y: currentY,
            });
            this.previousX = currentX;
            this.previousY = currentY;
        }
    }

    async saveSketch() {
        if (!this.sketchId) {
            alert('スケッチIDがありません。描画を開始してください。');
            return;
        }

        try {
            const linesResponse = await fetch('/api/save_lines', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sketch_id: this.sketchId, lines: this.currentLinesBuffer }),
            });

            if (!linesResponse.ok) {
                const errorResult = await linesResponse.json();
                throw new Error(`線の保存に失敗しました: ${errorResult.error || linesResponse.status}`);
            }

            const linesResult = await linesResponse.json();
            console.log('Lines saved:', linesResult.message);

            this.currentLinesBuffer = [];
            background(230);
            window.location.href = '';

        } catch (error) {
            console.error('スケッチの保存中にエラーが発生しました:', error);
            alert(`エラーが発生しました: ${error.message}`);
        }
    }
}

let mySketch; // グローバルスコープで宣言

function setup() {
    mySketch = new Sketch(); // setup 関数内で初期化
}

function draw() {
    if (mySketch) { // mySketch が初期化されているか確認
        mySketch.mouseDragged();
    }
}