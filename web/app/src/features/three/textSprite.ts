import * as THREE from "three";

export function makeTextSprite(text: string, opts?: { color?: string; fontSize?: number }) {
  const color = opts?.color ?? "#334155";
  const font = "bold 32px -apple-system, system-ui, Segoe UI, Roboto, sans-serif";
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return new THREE.Sprite(new THREE.SpriteMaterial({ color }));
  canvas.width = 320;
  canvas.height = 64;
  ctx.font = font;
  const w = ctx.measureText(text).width;
  ctx.fillStyle = "rgba(255,255,255,0)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.font = font;
  ctx.fillStyle = color;
  ctx.textBaseline = "middle";
  ctx.fillText(text, canvas.width / 2 - w / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(material);
  const scale = 0.0024;
  sprite.scale.set(canvas.width * scale, canvas.height * scale, 1);
  return sprite;
}