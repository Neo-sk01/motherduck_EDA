import { toPng } from "html-to-image";

export async function downloadElementPng(
  element: HTMLElement,
  filename: string,
): Promise<void> {
  const dataUrl = await toPng(element, {
    cacheBust: true,
    backgroundColor: "#ffffff",
    pixelRatio: 2,
  });
  const anchor = document.createElement("a");
  anchor.href = dataUrl;
  anchor.download = filename;
  anchor.click();
}
