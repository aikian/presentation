import cv2, mediapipe as mp, glob, os
mpfd = mp.solutions.face_detection
labels = {
 'kim_150':'중간샷 정면(양호)','kim_400':'객석 원경(불가)','kim_650':'중간샷 정면(양호)','kim_900':'청중샷(불가)',
 'mtN6m5mbqV4_150':'전신 원경','mtN6m5mbqV4_400':'전신 원경','mtN6m5mbqV4_650':'클로즈업','mtN6m5mbqV4_800':'청중샷(불가)',
 '7wHeV4nLtj8_150':'중간샷','7wHeV4nLtj8_400':'클로즈업','7wHeV4nLtj8_650':'클로즈업','7wHeV4nLtj8_800':'중간샷',
}
print(f"{'frame':<22}{'육안판정':<16}{'faces':>6}{'max_h%':>9}{'2nd_h%':>9}")
with mpfd.FaceDetection(model_selection=1, min_detection_confidence=0.4) as fd:
    for name, lab in labels.items():
        p = f'frames/{name}.jpg'
        if not os.path.exists(p): continue
        img = cv2.imread(p); h, w = img.shape[:2]
        r = fd.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        hs = sorted([d.location_data.relative_bounding_box.height for d in (r.detections or [])], reverse=True)
        m1 = hs[0]*100 if hs else 0
        m2 = hs[1]*100 if len(hs)>1 else 0
        print(f"{name:<22}{lab:<16}{len(hs):>6}{m1:>9.1f}{m2:>9.1f}")
