import time
from io import BytesIO
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel

class CaptchaAI:
    def __init__(self):
        print("Model yükleniyor (biraz zaman alabilir)...")
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        print("Model hazır.")

    def solve(self, image_bytes, target_label):
        img = Image.open(BytesIO(image_bytes))

        # Görseli 2x4 ızgaraya böl
        width, height = img.size
        tile_w = width // 4
        tile_h = height // 2

        images = []
        # Sıralama: Soldan sağa, yukarıdan aşağıya (0,1,2,3 üst satır, 4,5,6,7 alt satır)
        for row in range(2):
            for col in range(4):
                left = col * tile_w
                top = row * tile_h
                right = left + tile_w
                bottom = top + tile_h
                images.append(img.crop((left, top, right, bottom)))

        inputs = self.processor(text=[target_label], images=images, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)

        probs = outputs.logits_per_image.softmax(dim=0)
        best_match_idx = probs.argmax().item()
        confidence = probs[best_match_idx].item()

        print(f"AI Tahmini: Kutu #{best_match_idx} (Güven: %{confidence * 100:.2f})")
        return best_match_idx