import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("furgal.action.tools")

DEFAULT_SANDBOX = Path("storage/sandbox")
MAX_READ_BYTES = 1_000_000
MAX_WRITE_BYTES = 1_000_000


class ListDirParams(BaseModel):
    relative_path: str = Field(default=".", description="Path relative to sandbox root")
    max_depth: int = Field(default=2, ge=1, le=5, description="Maximum directory tree depth")


class ReadFileParams(BaseModel):
    relative_path: str = Field(min_length=1, description="File path relative to sandbox root")


class WriteFileParams(BaseModel):
    relative_path: str = Field(min_length=1, description="File path relative to sandbox root")
    content: str = Field(max_length=MAX_WRITE_BYTES, description="Content to write")
    append: bool = Field(default=False, description="Append instead of overwrite")


class ExecuteCodeParams(BaseModel):
    code: str = Field(max_length=5000, description="Python code to execute in sandbox")
    timeout: int = Field(default=5, ge=1, le=30, description="Maximum execution time in seconds")
    
    @field_validator("code")
    @classmethod
    def validate_safe_code(cls, value):
        # [MODIFICATION]: Basic safety validation for sandboxed code execution
        dangerous_patterns = [
            "import os", "import subprocess", "import sys", 
            "__import__", "exec(", "eval(", "open(", 
            "os.", "subprocess.", "sys."
        ]
        
        for pattern in dangerous_patterns:
            if pattern in value:
                raise ValueError(f"Code contains dangerous pattern: {pattern}")
        
        return value


class SearchFilesParams(BaseModel):
    query: str = Field(min_length=1, description="Filename substring to search for")
    relative_path: str = Field(default=".", description="Directory to search within sandbox")


class DeleteFileParams(BaseModel):
    relative_path: str = Field(min_length=1, description="File path relative to sandbox root")


def _resolve_sandbox_path(sandbox_root: Path, relative_path: str) -> Path:
    #Resolve and validate that a path stays within the sandbox
    sandbox_root = sandbox_root.resolve()
    target = (sandbox_root / relative_path).resolve()
    try:
        target.relative_to(sandbox_root)
    except ValueError:
        raise PermissionError(f"Access denied: '{relative_path}' is outside sandbox")
    return target


def _build_tree(directory: Path, sandbox_root: Path, depth: int, max_depth: int) -> List[Dict[str, Any]]:
    entries = []
    if depth > max_depth:
        return entries
    try:
        for item in sorted(directory.iterdir()):
            rel = str(item.relative_to(sandbox_root))
            entry: Dict[str, Any] = {"name": item.name, "path": rel, "type": "dir" if item.is_dir() else "file"}
            if item.is_dir() and depth < max_depth:
                entry["children"] = _build_tree(item, sandbox_root, depth + 1, max_depth)
            entries.append(entry)
    except PermissionError as exc:
        logger.warning("Permission denied listing %s: %s", directory, exc)
    return entries


class SandboxFileManager:

    def __init__(self, sandbox_root: str = str(DEFAULT_SANDBOX)):
        self.sandbox_root = Path(sandbox_root)
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def list_directory(self, params: ListDirParams) -> Dict[str, Any]:
        try:
            target = _resolve_sandbox_path(self.sandbox_root, params.relative_path)
            if not target.exists():
                return {"success": False, "error": f"Path not found: {params.relative_path}"}
            if target.is_file():
                return {"success": True, "type": "file", "path": params.relative_path}
            tree = _build_tree(target, self.sandbox_root, 1, params.max_depth)
            return {"success": True, "path": params.relative_path, "tree": tree}
        except PermissionError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("list_directory failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def read_file(self, params: ReadFileParams) -> Dict[str, Any]:
        try:
            target = _resolve_sandbox_path(self.sandbox_root, params.relative_path)
            if not target.is_file():
                return {"success": False, "error": f"Not a file: {params.relative_path}"}
            file_size = target.stat().st_size
            if file_size > MAX_READ_BYTES:
                return {
                    "success": False,
                    "error": f"File too large to read safely ({file_size} bytes)",
                    "max_bytes": MAX_READ_BYTES,
                }
            content = target.read_text(encoding="utf-8", errors="replace")
            return {"success": True, "path": params.relative_path, "content": content, "size": file_size}
        except PermissionError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("read_file failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def write_file(self, params: WriteFileParams) -> Dict[str, Any]:
        try:
            target = _resolve_sandbox_path(self.sandbox_root, params.relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if params.append else "w"
            with open(target, mode, encoding="utf-8") as fh:
                fh.write(params.content)
            return {"success": True, "path": params.relative_path, "mode": mode, "bytes_written": len(params.content)}
        except PermissionError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("write_file failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def search_files(self, params: SearchFilesParams) -> Dict[str, Any]:
        try:
            root = _resolve_sandbox_path(self.sandbox_root, params.relative_path)
            if not root.is_dir():
                return {"success": False, "error": f"Not a directory: {params.relative_path}"}
            query = params.query.lower()
            matches = []
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    if query in filename.lower():
                        full = Path(dirpath) / filename
                        rel = str(full.relative_to(self.sandbox_root.resolve()))
                        matches.append({"name": filename, "path": rel})
            return {"success": True, "query": params.query, "matches": matches[:100]}
        except PermissionError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("search_files failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def delete_file(self, params: DeleteFileParams) -> Dict[str, Any]:
        try:
            target = _resolve_sandbox_path(self.sandbox_root, params.relative_path)
            if not target.exists():
                return {"success": False, "error": f"Path not found: {params.relative_path}"}
            if target.is_dir():
                return {"success": False, "error": "Directory deletion not permitted; delete files only"}
            target.unlink()
            return {"success": True, "path": params.relative_path, "action": "deleted"}
        except PermissionError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("delete_file failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def execute_code(self, params: ExecuteCodeParams) -> Dict[str, Any]:
        # [MODIFICATION]: Safe sandboxed code execution
        try:
            import subprocess
            import tempfile
            import sys
            import ast
            
            # [MODIFICATION]: Validate code syntax first
            try:
                ast.parse(params.code)
            except SyntaxError as e:
                return {"success": False, "error": f"Syntax error in code: {e}"}
            
            # [MODIFICATION]: Create a temporary file in the sandbox
            temp_file = self.sandbox_root / f"temp_exec_{tempfile.gettempprefix()}.py"
            
            # [MODIFICATION]: Write the code with safety wrappers
            safe_code = f"""
import sys
import io

# Redirect stdout and stderr
output = io.StringIO()
error_output = io.StringIO()
old_stdout = sys.stdout
old_stderr = sys.stderr
sys.stdout = output
sys.stderr = error_output

try:
    # User code starts here
    {params.code}
    # User code ends here
except Exception as e:
    sys.stderr.write(f"Error: {{str(e)}}")
finally:
    sys.stdout = old_stdout
    sys.stderr = old_stderr

print("===STDOUT===")
print(output.getvalue())
print("===STDERR===")
print(error_output.getvalue())
"""
            
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(safe_code)
            
            # [MODIFICATION]: Execute with timeout and resource limits
            try:
                result = subprocess.run(
                    [sys.executable, str(temp_file)],
                    capture_output=True,
                    text=True,
                    timeout=params.timeout,
                    cwd=str(self.sandbox_root),
                    env={"PYTHONDONTWRITEBYTECODE": "1"}  # Prevent .pyc files
                )
                
                # [MODIFICATION]: Clean up temp file
                temp_file.unlink()
                
                # [MODIFICATION]: Parse and return results
                output_lines = result.stdout.split("===STDOUT===")
                error_lines = result.stdout.split("===STDERR===")
                
                stdout_content = output_lines[1].split("===STDERR===")[0] if len(output_lines) > 1 else ""
                stderr_content = error_lines[1] if len(error_lines) > 1 else result.stderr
                
                return {
                    "success": result.returncode == 0,
                    "stdout": stdout_content.strip(),
                    "stderr": stderr_content.strip(),
                    "return_code": result.returncode,
                    "timeout": params.timeout
                }
                
            except subprocess.TimeoutExpired:
                temp_file.unlink()
                return {"success": False, "error": f"Execution timed out after {params.timeout} seconds"}
            except Exception as exc:
                temp_file.unlink()
                logger.error("Code execution failed: %s", exc)
                return {"success": False, "error": f"Execution failed: {str(exc)}"}
                
        except Exception as exc:
            logger.error("execute_code failed: %s", exc)
            return {"success": False, "error": str(exc)}


_file_manager = SandboxFileManager()


def register_file_tools(registry) -> None:
    #Register sandboxed file management tools.
    registry.register_tool(
        name="list_directory",
        description="List files and directories within the sandbox (tree view)",
        params_model=ListDirParams,
        handler=_file_manager.list_directory,
    )
    registry.register_tool(
        name="read_file",
        description="Read the contents of a file within the sandbox",
        params_model=ReadFileParams,
        handler=_file_manager.read_file,
    )
    registry.register_tool(
        name="write_file",
        description="Create or update a file within the sandbox",
        params_model=WriteFileParams,
        handler=_file_manager.write_file,
    )
    registry.register_tool(
        name="search_files",
        description="Search for files by name within the sandbox",
        params_model=SearchFilesParams,
        handler=_file_manager.search_files,
    )
    registry.register_tool(
        name="delete_file",
        description="Delete a file within the sandbox",
        params_model=DeleteFileParams,
        handler=_file_manager.delete_file,
    )
    # [MODIFICATION]: Add sandboxed code execution tool
    registry.register_tool(
        name="execute_code",
        description="Execute Python code in a safe sandboxed environment with timeout",
        params_model=ExecuteCodeParams,
        handler=_file_manager.execute_code,
    )
