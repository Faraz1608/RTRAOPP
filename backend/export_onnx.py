import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

# Configuration
MODEL_PATH = "models/risk_bert"
ONNX_PATH = "models/risk_bert.onnx"

def export_model():
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}. Train it first.")
        return

    print(f"Loading model from {MODEL_PATH}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
    model.eval()

    # Dummy input for export (Batch size 1, 128 tokens)
    dummy_input = tokenizer("This is a dummy sentence for ONNX export.", return_tensors="pt")
    
    print("Exporting to ONNX...")
    torch.onnx.export(
        model, 
        (dummy_input["input_ids"], dummy_input["attention_mask"]), 
        ONNX_PATH,
        input_names=["input_ids", "attention_mask"], 
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch_size", 1: "sequence_length"},
            "attention_mask": {0: "batch_size", 1: "sequence_length"},
            "logits": {0: "batch_size"}
        },
        opset_version=14
    )
    
    print(f"Model exported to {ONNX_PATH}")
    
    # Optional: Quantization (Int8)
    print("Quantizing model (Int8) for web optimization...")
    from onnxruntime.quantization import quantize_dynamic, QuantType
    
    quantized_model_path = "models/risk_bert_quantized.onnx"
    quantize_dynamic(
        ONNX_PATH,
        quantized_model_path,
        weight_type=QuantType.QUInt8
    )
    
    print(f"Quantized model saved to {quantized_model_path}")

if __name__ == "__main__":
    export_model()
