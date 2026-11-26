@echo off
title PDF to Markdown Converter (PyMuPDF4LLM)
echo Starting PDF to Markdown Converter...
python app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred while launching the application.
    pause
)
