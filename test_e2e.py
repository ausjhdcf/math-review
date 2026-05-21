"""End-to-end integration test for the math review tool."""
import httpx
import sys

BASE_URL = "http://127.0.0.1:8000"
errors = []

def check(name, condition, detail=""):
    msg = f"{'PASS' if condition else 'FAIL'}: {name}"
    if detail and not condition:
        msg += f" ({detail})"
    print(msg)
    if not condition:
        errors.append(name)
    return condition

def main():
    print("=== E2E Integration Test ===\n")

    # Test 1: Home page
    try:
        r = httpx.get(f"{BASE_URL}/")
        check("Home page returns 200", r.status_code == 200, f"got {r.status_code}")
        check("Home page contains 上传", "上传" in r.text)
    except Exception as e:
        check("Home page accessible", False, str(e))

    # Test 2: Knowledge page
    try:
        r = httpx.get(f"{BASE_URL}/knowledge")
        check("Knowledge page returns 200", r.status_code == 200, f"got {r.status_code}")
        check("Knowledge page contains 知识库", "知识库" in r.text)
    except Exception as e:
        check("Knowledge page accessible", False, str(e))

    # Test 3: Upload endpoint (may take 30-60s for AI APIs)
    try:
        import os
        test_img = os.path.join(os.path.dirname(__file__), "verify", "test_images", "1.jpg")
        with open(test_img, "rb") as f:
            files = {"file": ("1.jpg", f, "image/jpeg")}
            data = {"upload_type": "错题", "subject": "高数", "user_note": "测试上传"}
            r = httpx.post(f"{BASE_URL}/api/upload", files=files, data=data,
                          follow_redirects=False, timeout=120.0)
        check("Upload returns redirect (303)", r.status_code == 303, f"got {r.status_code}")
        redirect_url = r.headers.get("location", "")
        check("Redirect URL contains /result/", "/result/" in redirect_url, f"got {redirect_url}")
        if r.status_code == 500:
            print(f"  Response body (first 500 chars): {r.text[:500]}")
    except Exception as e:
        check("Upload endpoint works", False, str(e))

    # Test 4: Check knowledge page after upload
    try:
        r = httpx.get(f"{BASE_URL}/knowledge")
        check("Knowledge page still accessible after upload", r.status_code == 200, f"got {r.status_code}")
    except Exception as e:
        check("Knowledge page post-upload accessible", False, str(e))

    print(f"\n=== Results: {len([e for e in errors if e])}/{sum(1 for _ in [1])} failed ===")
    if errors:
        print("FAILED:", ", ".join(errors))
        sys.exit(1)
    else:
        print("ALL TESTS PASSED!")
        sys.exit(0)

if __name__ == "__main__":
    main()
