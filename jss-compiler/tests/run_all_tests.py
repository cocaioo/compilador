import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
MAIN_PY = PROJECT_ROOT / "src" / "main.py"

def run_script(script_path):
    print(f"Running: {script_path.name}...")
    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    enc = sys.stdout.encoding or 'utf-8'
    stdout_safe = res.stdout.encode(enc, errors='replace').decode(enc)
    stderr_safe = res.stderr.encode(enc, errors='replace').decode(enc)
    if res.returncode != 0:
        print(f"FAILED: {script_path.name}")
        print("Stdout:", stdout_safe)
        print("Stderr:", stderr_safe)
        return False
    print(f"SUCCESS: {script_path.name}\n{stdout_safe.strip()}")
    return True

def run_compiler(input_str, expected_exit_code=0):
    res = subprocess.run(
        [sys.executable, str(MAIN_PY), "-"],
        input=input_str,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if res.returncode != expected_exit_code:
        print(f"Compiler E2E test failed. Expected exit code {expected_exit_code}, got {res.returncode}")
        print("Stdout:", res.stdout)
        print("Stderr:", res.stderr)
        return False, res.stdout
    return True, res.stdout

def run_integration_tests():
    print("\nRunning E2E Integration Tests...")
    
    # Test 1: Complex correct code (should pass)
    code_valid = """
    class Retangulo {
        real x;
        real y;
        Retangulo constructor(real x, real y) {
            this.x = x;
            this.y = y;
        }
        real area() {
            return this.x * this.y;
        }
    }
    function void main() {
        let Retangulo r = new Retangulo(1.5, 2.0);
        let real a = r.area();
        console.log("Area:", a);
    }
    """
    ok, stdout = run_compiler(code_valid, 0)
    if not ok: return False
    
    # Test 2: Multiple syntax and lexical errors
    code_syntax_errors = """
    let int x = 10 y;
    let str s = "escape \\x";
    function void main() {
        int a;
    }
    """
    ok, stdout = run_compiler(code_syntax_errors, 1)
    if not ok: return False
    if "token inesperado 'y'" not in stdout.lower() or "escape invalido" not in stdout.lower() or "utilize a palavra-chave" not in stdout.lower():
        print("Failed to identify all syntax/lexical errors in integration test 2")
        print(stdout)
        return False
    
    # Test 3: Multiple semantic errors with cascade suppression
    code_semantic_errors = """
    function void main() {
        let int a = b + c; // b and c undeclared
        let str s = 10;    // type mismatch
    }
    """
    ok, stdout = run_compiler(code_semantic_errors, 1)
    if not ok: return False
    # Check that it has exactly 3 errors, not more (meaning cascade was suppressed)
    errs_count = stdout.lower().count("erro sem")
    if errs_count != 3:
        print(f"Expected 3 semantic errors (cascade suppressed), got {errs_count}:\n{stdout}")
        return False
        
    # Test 4: Missing braces in flow control statements (colleague's feature)
    code_braces_missing = """
    function void main() {
        let int x = 10;
        if (x > 5)
            x = 20;
        while (x < 30)
            x += 1;
        for (let int i = 0; i < 5; ++i)
            console.log(i);
    }
    """
    ok, stdout = run_compiler(code_braces_missing, 1)
    if not ok: return False
    # Check that it complained about missing opening brace `{` in all 3 loops/ifs
    if stdout.lower().count("esperava-se '{'") != 3:
        print(f"Expected 3 syntax errors about missing '{{', got:\n{stdout}")
        return False

    print("Integration E2E Tests SUCCESS!")
    return True

def main():
    print("========================================")
    # Run lexer, parser, and semantic test scripts
    success = True
    success &= run_script(TESTS_DIR / "lexer" / "run_lexer_tests.py")
    print("-" * 40)
    success &= run_script(TESTS_DIR / "parser" / "run_parser_tests.py")
    print("-" * 40)
    success &= run_script(TESTS_DIR / "run_semantic_tests.py")
    print("-" * 40)
    success &= run_script(TESTS_DIR / "run_backend_tests.py")
    print("-" * 40)
    
    # Run integration tests
    success &= run_integration_tests()
    
    print("========================================")
    if success:
        print("ALL TESTS PASSED SUCCESSFULLY! (100% Green)")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
