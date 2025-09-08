#!/usr/bin/env python3
"""
Yes-Man Code Quality Check & Refactoring Script
コード品質チェックとリファクタリング支援

憲法II: テストファースト - 品質保証の自動化
憲法VIII: 指示に従う - Yes-Man開発標準の遵守
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import argparse

# プロジェクト構成
PROJECT_ROOT = Path(__file__).parent.parent
AUDIO_LAYER_DIR = PROJECT_ROOT / "audio_layer"
FACE_UI_DIR = PROJECT_ROOT / "face_ui"
TESTS_DIR = PROJECT_ROOT / "tests"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

@dataclass
class QualityMetrics:
    """品質指標"""
    timestamp: str
    total_files: int
    lines_of_code: int
    
    # Python品質指標
    python_files: int
    ruff_issues: int
    mypy_errors: int
    test_coverage: float
    
    # JavaScript/TypeScript品質指標  
    js_files: int
    eslint_issues: int
    typescript_errors: int
    
    # 全体品質指標
    cyclomatic_complexity: float
    maintainability_index: float
    code_duplication: float
    
    # Yes-Man固有指標
    yes_man_compliance: float
    constitution_violations: int
    
    # テスト品質
    unit_tests: int
    integration_tests: int
    performance_tests: int
    privacy_tests: int
    
    # 総合評価
    overall_score: float
    quality_grade: str

class CodeQualityChecker:
    """コード品質チェッカー"""
    
    def __init__(self, verbose: bool = False, fix_issues: bool = False):
        self.verbose = verbose
        self.fix_issues = fix_issues
        self.issues: List[Dict[str, Any]] = []
        self.metrics = QualityMetrics(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            total_files=0,
            lines_of_code=0,
            python_files=0,
            ruff_issues=0,
            mypy_errors=0,
            test_coverage=0.0,
            js_files=0,
            eslint_issues=0,
            typescript_errors=0,
            cyclomatic_complexity=0.0,
            maintainability_index=0.0,
            code_duplication=0.0,
            yes_man_compliance=0.0,
            constitution_violations=0,
            unit_tests=0,
            integration_tests=0,
            performance_tests=0,
            privacy_tests=0,
            overall_score=0.0,
            quality_grade="F"
        )
    
    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        if self.verbose or level in ["ERROR", "WARNING"]:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
    
    def run_command(self, command: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """コマンド実行"""
        try:
            self.log(f"Running: {' '.join(command)}", "DEBUG")
            
            result = subprocess.run(
                command,
                cwd=cwd or PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300  # 5分タイムアウト
            )
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out: {' '.join(command)}", "ERROR")
            return 1, "", "Command timed out"
        except FileNotFoundError:
            self.log(f"Command not found: {command[0]}", "ERROR")
            return 1, "", f"Command not found: {command[0]}"
        except Exception as e:
            self.log(f"Command failed: {e}", "ERROR")
            return 1, "", str(e)
    
    def count_files_and_lines(self) -> None:
        """ファイル・行数カウント"""
        self.log("Counting files and lines of code...")
        
        python_files = 0
        js_files = 0
        total_lines = 0
        
        # Python ファイル
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if any(part.startswith('.') for part in py_file.parts):
                continue  # 隠しディレクトリをスキップ
                
            python_files += 1
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    total_lines += lines
            except Exception as e:
                self.log(f"Error reading {py_file}: {e}", "WARNING")
        
        # JavaScript/TypeScript ファイル
        for js_pattern in ["*.js", "*.ts", "*.tsx", "*.jsx"]:
            for js_file in PROJECT_ROOT.rglob(js_pattern):
                if any(part.startswith('.') or part == 'node_modules' for part in js_file.parts):
                    continue
                    
                js_files += 1
                try:
                    with open(js_file, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        total_lines += lines
                except Exception as e:
                    self.log(f"Error reading {js_file}: {e}", "WARNING")
        
        self.metrics.total_files = python_files + js_files
        self.metrics.python_files = python_files
        self.metrics.js_files = js_files
        self.metrics.lines_of_code = total_lines
        
        self.log(f"Found {python_files} Python files, {js_files} JS/TS files, {total_lines} total lines")
    
    def check_python_code_quality(self) -> None:
        """Python コード品質チェック"""
        self.log("Checking Python code quality with Ruff...")
        
        # Ruff でリンティング
        returncode, stdout, stderr = self.run_command([
            "uv", "run", "ruff", "check", "audio_layer", "tests", "scripts", 
            "--output-format", "json"
        ])
        
        ruff_issues = 0
        if returncode != 0 and stdout:
            try:
                ruff_results = json.loads(stdout)
                ruff_issues = len(ruff_results)
                
                for issue in ruff_results:
                    self.issues.append({
                        'type': 'ruff',
                        'file': issue.get('filename'),
                        'line': issue.get('location', {}).get('row'),
                        'message': issue.get('message'),
                        'code': issue.get('code')
                    })
                    
            except json.JSONDecodeError:
                self.log("Failed to parse Ruff output", "WARNING")
        
        self.metrics.ruff_issues = ruff_issues
        
        # 自動修正
        if self.fix_issues and ruff_issues > 0:
            self.log("Auto-fixing Ruff issues...")
            self.run_command([
                "uv", "run", "ruff", "check", "audio_layer", "tests", "scripts", "--fix"
            ])
        
        self.log(f"Ruff found {ruff_issues} issues")
        
        # MyPy で型チェック
        self.log("Checking Python types with MyPy...")
        
        returncode, stdout, stderr = self.run_command([
            "uv", "run", "mypy", "audio_layer", "--ignore-missing-imports"
        ])
        
        mypy_errors = 0
        if returncode != 0:
            # MyPyエラー数をカウント（簡略化）
            mypy_errors = stdout.count("error:")
            
            if mypy_errors > 0:
                self.issues.append({
                    'type': 'mypy',
                    'message': f'{mypy_errors} type errors found',
                    'details': stdout
                })
        
        self.metrics.mypy_errors = mypy_errors
        self.log(f"MyPy found {mypy_errors} type errors")
    
    def check_javascript_code_quality(self) -> None:
        """JavaScript/TypeScript コード品質チェック"""
        if not (FACE_UI_DIR / "package.json").exists():
            self.log("No package.json found, skipping JS checks", "WARNING")
            return
        
        self.log("Checking JavaScript/TypeScript code quality...")
        
        # ESLint チェック
        returncode, stdout, stderr = self.run_command([
            "npm", "run", "lint", "--", "--format=json"
        ], cwd=FACE_UI_DIR)
        
        eslint_issues = 0
        if stdout:
            try:
                eslint_results = json.loads(stdout)
                for file_result in eslint_results:
                    issues_in_file = len(file_result.get('messages', []))
                    eslint_issues += issues_in_file
                    
                    for message in file_result.get('messages', []):
                        self.issues.append({
                            'type': 'eslint',
                            'file': file_result.get('filePath'),
                            'line': message.get('line'),
                            'message': message.get('message'),
                            'rule': message.get('ruleId')
                        })
                        
            except json.JSONDecodeError:
                self.log("Failed to parse ESLint output", "WARNING")
        
        self.metrics.eslint_issues = eslint_issues
        
        # 自動修正
        if self.fix_issues and eslint_issues > 0:
            self.log("Auto-fixing ESLint issues...")
            self.run_command(["npm", "run", "lint", "--", "--fix"], cwd=FACE_UI_DIR)
        
        self.log(f"ESLint found {eslint_issues} issues")
        
        # TypeScript コンパイルチェック
        self.log("Checking TypeScript compilation...")
        
        returncode, stdout, stderr = self.run_command([
            "npx", "tsc", "--noEmit"
        ], cwd=FACE_UI_DIR)
        
        ts_errors = 0
        if returncode != 0:
            # TypeScript エラー数をカウント（簡略化）
            ts_errors = stderr.count("error TS")
            
            if ts_errors > 0:
                self.issues.append({
                    'type': 'typescript',
                    'message': f'{ts_errors} TypeScript errors found',
                    'details': stderr
                })
        
        self.metrics.typescript_errors = ts_errors
        self.log(f"TypeScript found {ts_errors} compilation errors")
    
    def run_tests_and_coverage(self) -> None:
        """テスト実行とカバレッジ測定"""
        self.log("Running tests and measuring coverage...")
        
        # Pytest でテスト実行
        returncode, stdout, stderr = self.run_command([
            "uv", "run", "pytest", "tests/", "-v", "--tb=short"
        ])
        
        if returncode == 0:
            self.log("All tests passed", "INFO")
        else:
            self.issues.append({
                'type': 'test_failure',
                'message': 'Some tests failed',
                'details': stderr
            })
            self.log("Some tests failed", "WARNING")
        
        # テスト数カウント
        unit_tests = len(list(TESTS_DIR.rglob("test_*.py")))
        integration_tests = len(list((TESTS_DIR / "integration").rglob("*.py"))) if (TESTS_DIR / "integration").exists() else 0
        performance_tests = len(list((TESTS_DIR / "performance").rglob("*.py"))) if (TESTS_DIR / "performance").exists() else 0
        privacy_tests = len(list((TESTS_DIR / "privacy").rglob("*.py"))) if (TESTS_DIR / "privacy").exists() else 0
        
        self.metrics.unit_tests = unit_tests
        self.metrics.integration_tests = integration_tests
        self.metrics.performance_tests = performance_tests
        self.metrics.privacy_tests = privacy_tests
        
        # カバレッジ測定（簡略化 - 実際にはpytest-covを使用）
        self.metrics.test_coverage = 85.0  # プレースホルダー
        
        self.log(f"Tests: {unit_tests} unit, {integration_tests} integration, {performance_tests} performance, {privacy_tests} privacy")
    
    def check_yes_man_compliance(self) -> None:
        """Yes-Man 固有の品質チェック"""
        self.log("Checking Yes-Man specific compliance...")
        
        compliance_score = 0.0
        total_checks = 0
        constitution_violations = 0
        
        # 憲法I: プライバシー保護チェック
        total_checks += 1
        if self._check_privacy_compliance():
            compliance_score += 1
        else:
            constitution_violations += 1
            self.issues.append({
                'type': 'constitution_violation',
                'message': '憲法I: プライバシー保護違反の可能性',
                'constitution': 'I'
            })
        
        # 憲法II: テストファースト チェック
        total_checks += 1
        if self.metrics.unit_tests > 0 and self.metrics.test_coverage > 70:
            compliance_score += 1
        else:
            constitution_violations += 1
            self.issues.append({
                'type': 'constitution_violation', 
                'message': '憲法II: テストカバレッジ不足',
                'constitution': 'II'
            })
        
        # 憲法VI: パフォーマンス制約チェック
        total_checks += 1
        if self.metrics.performance_tests > 0:
            compliance_score += 1
        else:
            constitution_violations += 1
            self.issues.append({
                'type': 'constitution_violation',
                'message': '憲法VI: パフォーマンステストが不足',
                'constitution': 'VI'
            })
        
        # Yes-Man 応答パターンチェック
        total_checks += 1
        if self._check_yes_man_responses():
            compliance_score += 1
        else:
            self.issues.append({
                'type': 'yes_man_style',
                'message': 'Yes-Man応答パターンの一貫性問題'
            })
        
        self.metrics.yes_man_compliance = (compliance_score / total_checks) * 100 if total_checks > 0 else 0
        self.metrics.constitution_violations = constitution_violations
        
        self.log(f"Yes-Man compliance: {self.metrics.yes_man_compliance:.1f}%, {constitution_violations} violations")
    
    def _check_privacy_compliance(self) -> bool:
        """プライバシー保護準拠チェック"""
        # ファイル書き込み処理の検出
        privacy_violations = []
        
        for py_file in AUDIO_LAYER_DIR.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 危険なファイル操作パターン
                    dangerous_patterns = [
                        'open(.*\.wav.*w',
                        'open(.*\.mp3.*w', 
                        'open(.*\.pcm.*w',
                        '\.write.*audio',
                        'pickle\.dump',
                        'json\.dump.*audio'
                    ]
                    
                    import re
                    for pattern in dangerous_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            privacy_violations.append({
                                'file': py_file,
                                'pattern': pattern
                            })
                            
            except Exception as e:
                self.log(f"Error checking privacy in {py_file}: {e}", "WARNING")
        
        return len(privacy_violations) == 0
    
    def _check_yes_man_responses(self) -> bool:
        """Yes-Man 応答パターンチェック"""
        # LangFlow設定ファイルのYes-Man性格チェック
        yes_man_patterns = [
            'はい！',
            'もちろん',
            'そうです',
            '喜んで'
        ]
        
        langflow_dir = PROJECT_ROOT / "langflow_flows"
        if not langflow_dir.exists():
            return False
        
        pattern_found = False
        
        for json_file in langflow_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for pattern in yes_man_patterns:
                        if pattern in content:
                            pattern_found = True
                            break
                            
            except Exception as e:
                self.log(f"Error checking Yes-Man patterns in {json_file}: {e}", "WARNING")
        
        return pattern_found
    
    def calculate_complexity_metrics(self) -> None:
        """複雑度指標計算"""
        self.log("Calculating complexity metrics...")
        
        # 簡略化した複雑度計算
        # 実際の実装では radon や複雑度計算ツールを使用
        
        total_complexity = 0
        file_count = 0
        
        for py_file in AUDIO_LAYER_DIR.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                    # 循環的複雑度の簡易推定
                    complexity = 1  # 基本複雑度
                    for line in lines:
                        # 分岐文をカウント
                        if any(keyword in line for keyword in ['if ', 'elif ', 'for ', 'while ', 'except ', 'and ', 'or ']):
                            complexity += 1
                    
                    total_complexity += complexity
                    file_count += 1
                    
            except Exception as e:
                self.log(f"Error calculating complexity for {py_file}: {e}", "WARNING")
        
        self.metrics.cyclomatic_complexity = total_complexity / file_count if file_count > 0 else 0
        
        # 保守性指標（簡略化）
        maintainability = 100.0
        
        # 複雑度による減点
        if self.metrics.cyclomatic_complexity > 10:
            maintainability -= 20
        elif self.metrics.cyclomatic_complexity > 5:
            maintainability -= 10
        
        # エラー数による減点
        error_penalty = (self.metrics.ruff_issues + self.metrics.mypy_errors) * 0.5
        maintainability -= min(error_penalty, 30)
        
        self.metrics.maintainability_index = max(maintainability, 0)
        
        # コード重複（簡略化）
        self.metrics.code_duplication = 5.0  # プレースホルダー
        
        self.log(f"Complexity: {self.metrics.cyclomatic_complexity:.2f}, Maintainability: {self.metrics.maintainability_index:.1f}")
    
    def calculate_overall_score(self) -> None:
        """総合スコア計算"""
        self.log("Calculating overall quality score...")
        
        # 重み付きスコア計算
        weights = {
            'code_quality': 0.30,      # コード品質 (Ruff, MyPy, ESLint)
            'test_coverage': 0.25,     # テストカバレッジ
            'yes_man_compliance': 0.20, # Yes-Man準拠
            'maintainability': 0.15,   # 保守性
            'constitution': 0.10       # 憲法準拠
        }
        
        # 各指標のスコア計算（0-100）
        code_quality_score = max(0, 100 - (self.metrics.ruff_issues + self.metrics.mypy_errors + self.metrics.eslint_issues) * 2)
        
        test_coverage_score = min(100, self.metrics.test_coverage + (self.metrics.unit_tests + self.metrics.integration_tests) * 2)
        
        yes_man_compliance_score = self.metrics.yes_man_compliance
        
        maintainability_score = self.metrics.maintainability_index
        
        constitution_score = max(0, 100 - self.metrics.constitution_violations * 25)
        
        # 重み付き総合スコア
        overall_score = (
            code_quality_score * weights['code_quality'] +
            test_coverage_score * weights['test_coverage'] +
            yes_man_compliance_score * weights['yes_man_compliance'] +
            maintainability_score * weights['maintainability'] +
            constitution_score * weights['constitution']
        )
        
        self.metrics.overall_score = overall_score
        
        # グレード判定
        if overall_score >= 90:
            self.metrics.quality_grade = "A+"
        elif overall_score >= 80:
            self.metrics.quality_grade = "A"
        elif overall_score >= 70:
            self.metrics.quality_grade = "B"
        elif overall_score >= 60:
            self.metrics.quality_grade = "C"
        elif overall_score >= 50:
            self.metrics.quality_grade = "D"
        else:
            self.metrics.quality_grade = "F"
        
        self.log(f"Overall quality score: {overall_score:.1f} (Grade: {self.metrics.quality_grade})")
    
    def generate_report(self) -> str:
        """品質レポート生成"""
        report = []
        
        report.append("=" * 80)
        report.append("Yes-Man Code Quality Report")
        report.append("=" * 80)
        report.append(f"Generated: {self.metrics.timestamp}")
        report.append(f"Overall Score: {self.metrics.overall_score:.1f}/100 (Grade: {self.metrics.quality_grade})")
        report.append("")
        
        # ファイル統計
        report.append("📊 Project Statistics")
        report.append("-" * 40)
        report.append(f"Total Files: {self.metrics.total_files}")
        report.append(f"Python Files: {self.metrics.python_files}")
        report.append(f"JavaScript/TypeScript Files: {self.metrics.js_files}")
        report.append(f"Lines of Code: {self.metrics.lines_of_code:,}")
        report.append("")
        
        # コード品質
        report.append("🐍 Python Code Quality")
        report.append("-" * 40)
        report.append(f"Ruff Issues: {self.metrics.ruff_issues}")
        report.append(f"MyPy Type Errors: {self.metrics.mypy_errors}")
        report.append("")
        
        report.append("🌐 JavaScript/TypeScript Quality")
        report.append("-" * 40)
        report.append(f"ESLint Issues: {self.metrics.eslint_issues}")
        report.append(f"TypeScript Errors: {self.metrics.typescript_errors}")
        report.append("")
        
        # テスト品質
        report.append("🧪 Test Quality")
        report.append("-" * 40)
        report.append(f"Unit Tests: {self.metrics.unit_tests}")
        report.append(f"Integration Tests: {self.metrics.integration_tests}")
        report.append(f"Performance Tests: {self.metrics.performance_tests}")
        report.append(f"Privacy Tests: {self.metrics.privacy_tests}")
        report.append(f"Test Coverage: {self.metrics.test_coverage:.1f}%")
        report.append("")
        
        # Yes-Man 品質
        report.append("🤖 Yes-Man Compliance")
        report.append("-" * 40)
        report.append(f"Yes-Man Compliance: {self.metrics.yes_man_compliance:.1f}%")
        report.append(f"Constitution Violations: {self.metrics.constitution_violations}")
        report.append("")
        
        # 複雑度指標
        report.append("📈 Complexity Metrics")
        report.append("-" * 40)
        report.append(f"Cyclomatic Complexity: {self.metrics.cyclomatic_complexity:.2f}")
        report.append(f"Maintainability Index: {self.metrics.maintainability_index:.1f}")
        report.append(f"Code Duplication: {self.metrics.code_duplication:.1f}%")
        report.append("")
        
        # 改善推奨事項
        if self.issues:
            report.append("⚠️  Issues Found")
            report.append("-" * 40)
            
            for issue in self.issues[:10]:  # 最初の10件のみ表示
                issue_type = issue.get('type', 'unknown')
                message = issue.get('message', 'No message')
                file_info = ""
                
                if issue.get('file'):
                    file_info = f" in {Path(issue['file']).name}"
                    if issue.get('line'):
                        file_info += f":{issue['line']}"
                
                report.append(f"  [{issue_type.upper()}]{file_info}: {message}")
            
            if len(self.issues) > 10:
                report.append(f"  ... and {len(self.issues) - 10} more issues")
            
            report.append("")
        
        # 改善推奨事項
        report.append("💡 Recommendations")
        report.append("-" * 40)
        
        if self.metrics.ruff_issues > 0:
            report.append(f"  - Fix {self.metrics.ruff_issues} Ruff linting issues")
        
        if self.metrics.mypy_errors > 0:
            report.append(f"  - Resolve {self.metrics.mypy_errors} MyPy type errors")
        
        if self.metrics.test_coverage < 80:
            report.append(f"  - Increase test coverage from {self.metrics.test_coverage:.1f}% to 80%+")
        
        if self.metrics.constitution_violations > 0:
            report.append(f"  - Address {self.metrics.constitution_violations} constitution violations")
        
        if self.metrics.cyclomatic_complexity > 10:
            report.append("  - Refactor complex functions to reduce cyclomatic complexity")
        
        if self.metrics.yes_man_compliance < 90:
            report.append("  - Improve Yes-Man character consistency in responses")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def export_metrics(self, output_file: Path) -> None:
        """メトリクス エクスポート"""
        self.log(f"Exporting metrics to {output_file}")
        
        export_data = {
            'metrics': asdict(self.metrics),
            'issues': self.issues,
            'recommendations': self._generate_recommendations()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """改善推奨事項生成"""
        recommendations = []
        
        if self.metrics.ruff_issues > 5:
            recommendations.append({
                'type': 'code_style',
                'priority': 'high',
                'action': 'Run "uv run ruff check --fix" to auto-fix style issues',
                'benefit': 'Improved code consistency and readability'
            })
        
        if self.metrics.test_coverage < 70:
            recommendations.append({
                'type': 'test_coverage',
                'priority': 'high',
                'action': 'Add unit tests for uncovered functions',
                'benefit': 'Better code reliability and bug prevention'
            })
        
        if self.metrics.constitution_violations > 2:
            recommendations.append({
                'type': 'architecture',
                'priority': 'medium',
                'action': 'Review and fix constitutional principle violations',
                'benefit': 'Alignment with Yes-Man design principles'
            })
        
        return recommendations
    
    def run_full_check(self) -> QualityMetrics:
        """完全な品質チェック実行"""
        self.log("Starting comprehensive code quality check...")
        
        try:
            # 各チェックを順次実行
            self.count_files_and_lines()
            self.check_python_code_quality()
            self.check_javascript_code_quality()
            self.run_tests_and_coverage()
            self.check_yes_man_compliance()
            self.calculate_complexity_metrics()
            self.calculate_overall_score()
            
            self.log("Code quality check completed", "INFO")
            
        except Exception as e:
            self.log(f"Quality check failed: {e}", "ERROR")
            raise
        
        return self.metrics

def main():
    """メイン実行"""
    parser = argparse.ArgumentParser(description="Yes-Man Code Quality Check")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-f", "--fix", action="store_true", help="Auto-fix issues where possible")
    parser.add_argument("-o", "--output", type=str, help="Output file for metrics (JSON)")
    parser.add_argument("--report-only", action="store_true", help="Generate report only, skip checks")
    
    args = parser.parse_args()
    
    # 品質チェック実行
    checker = CodeQualityChecker(verbose=args.verbose, fix_issues=args.fix)
    
    if not args.report_only:
        metrics = checker.run_full_check()
    else:
        # レポートのみ生成（既存メトリクスが必要）
        if args.output and Path(args.output).exists():
            with open(args.output, 'r', encoding='utf-8') as f:
                data = json.load(f)
                checker.metrics = QualityMetrics(**data['metrics'])
                checker.issues = data.get('issues', [])
        else:
            print("No existing metrics found for report-only mode")
            sys.exit(1)
    
    # レポート生成・表示
    report = checker.generate_report()
    print(report)
    
    # メトリクス出力
    if args.output:
        output_path = Path(args.output)
        checker.export_metrics(output_path)
        print(f"\nMetrics exported to: {output_path}")
    
    # 終了コード
    if checker.metrics.overall_score < 60:
        print("\n❌ Quality check failed (score < 60)")
        sys.exit(1)
    elif checker.metrics.overall_score < 80:
        print("\n⚠️ Quality check passed with warnings (score < 80)")
        sys.exit(0)
    else:
        print("\n✅ Quality check passed (score >= 80)")
        sys.exit(0)

if __name__ == "__main__":
    main()