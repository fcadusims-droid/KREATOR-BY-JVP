"""Local, offline VLM backend — describes a frame on CPU, no GPU, no API.

Uses SmolVLM (2.2B) via transformers. Heavy imports are lazy and the model is
loaded once, so importing ``kreator.vlm`` stays cheap and the rest of the
pipeline runs without torch installed. Asks the model only to *describe* the
frame; the scene decision is made deterministically in ``classify``.

Measured on this CPU (4 cores, no GPU): ~28–50 s to load, ~45–50 s per frame.
That's why the VLM runs on a *sampled* handful of keyframes, not every frame,
and is opt-in — it's an offline enrichment pass, not an interactive step.
"""

from __future__ import annotations

_DESCRIBE_PROMPT = (
    "What is happening in this video game screenshot? "
    "Describe it in one short sentence."
)


class LocalVLMBackend:
    name = "smolvlm-2.2b"

    def __init__(self, model_id: str = "HuggingFaceTB/SmolVLM-Instruct") -> None:
        self.model_id = model_id
        self._proc = None
        self._model = None

    def _ensure_loaded(self) -> None:  # pragma: no cover - heavy, needs weights
        if self._model is not None:
            return
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self._proc = AutoProcessor.from_pretrained(self.model_id)
        self._model = AutoModelForImageTextToText.from_pretrained(
            self.model_id, dtype="float32"
        )
        self._model.eval()

    def describe(self, image_path: str) -> str:  # pragma: no cover - needs weights
        """Return a one-sentence description of the frame at ``image_path``."""
        import torch
        from PIL import Image

        self._ensure_loaded()
        img = Image.open(image_path).convert("RGB")
        messages = [{"role": "user", "content": [
            {"type": "image"}, {"type": "text", "text": _DESCRIBE_PROMPT}]}]
        text = self._proc.apply_chat_template(messages, add_generation_prompt=True)
        inputs = self._proc(text=text, images=[img], return_tensors="pt")
        with torch.no_grad():
            out = self._model.generate(**inputs, max_new_tokens=70, do_sample=False)
        decoded = self._proc.batch_decode(out, skip_special_tokens=True)[0]
        return decoded.split("Assistant:")[-1].strip().replace("\n", " ")
