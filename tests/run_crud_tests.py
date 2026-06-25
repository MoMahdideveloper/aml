#!/usr/bin/env python3
"""
Comprehensive test runner for CRUD operations
Runs all CRUD-related tests and generates a detailed report
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test_suite(test_file, description):
    """Run a specific test suite and return results"""
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            test_file, 
            '-v', 
            '--tb=short',
            '--no-header'
        ], capture_output=True, text=True, cwd=project_root)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Duration: {duration:.2f} seconds")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("\nSTDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        return {
            'file': test_file,
            'description': description,
            'returncode': result.returncode,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
        
    except Exception as e:
        print(f"Error running {test_file}: {e}")
        return {
            'file': test_file,
            'description': description,
            'returncode': -1,
            'duration': 0,
            'stdout': '',
            'stderr': str(e),
            'success': False
        }

def run_javascript_tests():
    """Run JavaScript tests"""
    print(f"\n{'='*60}")
    print("Running JavaScript Tests")
    print(f"{'='*60}")
    
    # Check if Node.js is available
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("Node.js not available, skipping JavaScript tests")
            return {'success': False, 'reason': 'Node.js not available'}
    except FileNotFoundError:
        print("Node.js not found, skipping JavaScript tests")
        return {'success': False, 'reason': 'Node.js not found'}
    
    # Check if Jest is available
    jest_available = False
    try:
        result = subprocess.run(['npx', 'jest', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            jest_available = True
    except FileNotFoundError:
        pass
    
    if jest_available:
        # Run with Jest
        try:
            result = subprocess.run([
                'npx', 'jest', 
                'tests/test_crud_utils.js',
                '--verbose'
            ], capture_output=True, text=True, cwd=project_root)
            
            print(f"Jest return code: {result.returncode}")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
                
            return {'success': result.returncode == 0, 'method': 'Jest'}
        except Exception as e:
            print(f"Error running Jest: {e}")
    
    # Fallback to Node.js direct execution
    try:
        result = subprocess.run([
            'node', 
            'tests/test_crud_utils.js'
        ], capture_output=True, text=True, cwd=project_root)
        
        print(f"Node.js return code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        return {'success': result.returncode == 0, 'method': 'Node.js'}
    except Exception as e:
        print(f"Error running Node.js tests: {e}")
        return {'success': False, 'reason': str(e)}

def generate_report(results, js_result):
    """Generate a comprehensive test report"""
    print(f"\n{'='*80}")
    print("COMPREHENSIVE CRUD TEST REPORT")
    print(f"{'='*80}")
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - successful_tests
    
    print(f"\nPython Test Summary:")
    print(f"  Total test suites: {total_tests}")
    print(f"  Successful: {successful_tests}")
    print(f"  Failed: {failed_tests}")
    print(f"  Success rate: {(successful_tests/total_tests)*100:.1f}%")
    
    total_duration = sum(r['duration'] for r in results)
    print(f"  Total duration: {total_duration:.2f} seconds")
    
    print(f"\nJavaScript Test Summary:")
    if js_result['success']:
        print(f"  Status: PASSED ({js_result.get('method', 'Unknown method')})")
    else:
        print(f"  Status: FAILED ({js_result.get('reason', 'Unknown error')})")
    
    print(f"\nDetailed Results:")
    print(f"{'-'*80}")
    
    for result in results:
        status = "PASS" if result['success'] else "FAIL"
        print(f"[{status}] {result['description']}")
        print(f"        File: {result['file']}")
        print(f"        Duration: {result['duration']:.2f}s")
        
        if not result['success']:
            print(f"        Error: Return code {result['returncode']}")
            if result['stderr']:
                # Show first few lines of stderr
                stderr_lines = result['stderr'].split('\n')[:3]
                for line in stderr_lines:
                    if line.strip():
                        print(f"        {line}")
        print()
    
    # Overall status
    overall_success = successful_tests == total_tests and js_result['success']
    print(f"{'='*80}")
    print(f"OVERALL STATUS: {'PASS' if overall_success else 'FAIL'}")
    print(f"{'='*80}")
    
    return overall_success

def main():
    """Main test runner function"""
    print("CRUD Operations Test Suite")
    print("=" * 50)
    
    # Define test suites
    test_suites = [
        ('tests/test_crud_database_service.py', 'Database Service CRUD Tests'),
        ('tests/test_crud_forms.py', 'Form Validation Tests'),
        ('tests/test_agent_crud_routes.py', 'Agent CRUD Routes Tests'),
        ('tests/test_deal_crud_routes.py', 'Deal CRUD Routes Tests'),
        ('tests/test_crud_routes.py', 'Comprehensive CRUD Routes Tests'),
        ('tests/test_crud_integration.py', 'End-to-End Integration Tests'),
    ]
    
    # Run Python test suites
    results = []
    for test_file, description in test_suites:
        if os.path.exists(os.path.join(project_root, test_file)):
            result = run_test_suite(test_file, description)
            results.append(result)
        else:
            print(f"Warning: Test file {test_file} not found, skipping...")
            results.append({
                'file': test_file,
                'description': description,
                'returncode': -1,
                'duration': 0,
                'stdout': '',
                'stderr': 'File not found',
                'success': False
            })
    
    # Run JavaScript tests
    js_result = run_javascript_tests()
    
    # Generate comprehensive report
    overall_success = generate_report(results, js_result)
    
    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)

if __name__ == '__main__':
    main()
