import easyocr

reader = easyocr.Reader(['en'])

def read_plate(frame):
    results = reader.readtext(frame)

    for (bbox, text, prob) in results:
        if prob > 0.5:
            return text

    return "Unknown"