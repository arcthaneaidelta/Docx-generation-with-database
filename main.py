from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from docxtpl import DocxTemplate, RichText
from jinja2 import Environment, StrictUndefined
import uvicorn
import os
import io
import logging
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define input schema
class DemandLetterData(BaseModel):
    date: str = ""
    defendant: str = ""
    street_address: str = ""
    state_address: str = ""
    plaintiff_full_name: str = ""
    pronoun: str = ""
    clauses: str = ""
    mr_ms_last_name: str = ""
    start_date: str = ""
    job_title: str = ""
    hourly_wage_annual_salary: str = ""
    end_date: str = ""
    paragraphs_concerning_wrongful_termination: str = ""
    paragraphs_concerning_labor_code_violations: str = ""
    delete_a_or_b: str = ""
    damages_formatted: str = ""
    conclusion: str = ""
    company_name: str = ""
    client_name: str = ""

app = FastAPI(
    title="Demand Letter Generator API",
    version="1.0.0",
    description="A robust API for generating demand letters with rich text formatting"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

def create_rich_text_field(text: str, bold: bool = False, underline: bool = False, italic: bool = False, size: int = 24, font: str = 'Times New Roman') -> RichText:
    """
    Create a RichText object with specified formatting
    
    Args:
        text: The text content
        bold: Apply bold formatting
        underline: Apply underline formatting
        italic: Apply italic formatting
    
    Returns:
        RichText object with applied formatting
    """
    if not text or text.strip() == "":
        return RichText("")
    
    rt = RichText()
    rt.add(str(text), bold=bold, underline=underline, italic=italic, size=size, font=font)
    return rt

def prepare_context_with_styling(data: DemandLetterData) -> dict:
    """
    Prepare context dictionary with appropriate styling for each field
    
    Args:
        data: Input data model
    
    Returns:
        Dictionary with styled RichText objects and plain text
    """
    context = {}
    data_dict = data.model_dump()
    
    # Fields that should be bold only
    bold_fields = [
        'defendant', 'street_address', 'state_address', 'plaintiff_full_name',
        'pronoun', 'mr_ms_last_name', 'start_date', 'job_title', 
        'hourly_wage_annual_salary', 'end_date', 'company_name', 
        'client_name', 'damages_formatted'
    ]
    
    # Fields that should be bold and underlined
    bold_underlined_fields = ['date']
    
    # Fields with no styling (plain text)
    no_style_fields = [
        'conclusion', 'paragraphs_concerning_labor_code_violations',
        'paragraphs_concerning_wrongful_termination', 'clauses'
    ]
    
    # Apply styling based on field categories
    for field, value in data_dict.items():
        # Convert None to empty string
        if value is None:
            value = ""
        
        if field in bold_fields:
            context[field] = create_rich_text_field(value, bold=True)
        elif field in bold_underlined_fields:
            context[field] = create_rich_text_field(value, bold=True, underline=True)
        elif field in no_style_fields:
            # Keep as plain string for no styling
            context[field] = str(value)
        else:
            # Default handling for any fields not explicitly categorized
            context[field] = str(value)
    
    # Handle the delete_a_or_b field (not specified, treating as plain text)
    if 'delete_a_or_b' in context:
        context['delete_a_or_b'] = str(data_dict.get('delete_a_or_b', ''))
    
    return context

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Demand Letter API is running", 
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    template_exists = Path("template2.docx").exists()
    return {
        "status": "healthy" if template_exists else "degraded",
        "service": "demand-letter-generator",
        "template_available": template_exists,
        "version": "1.0.0"
    }

@app.get("/template-info")
async def template_info():
    """Get information about the template file"""
    template_path = Path("template.docx")
    if template_path.exists():
        size = template_path.stat().st_size
        return {
            "template_exists": True,
            "template_size": size,
            "template_path": str(template_path.absolute())
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="Template file not found"
        )

@app.post("/generate-letter")
async def generate_letter(data: DemandLetterData):
    """
    Generate a demand letter from template with rich text formatting
    
    Returns a downloadable DOCX file with properly formatted content
    """
    
    try:
        # Validate template exists
        template_path = Path("template.docx")
        if not template_path.exists():
            logger.error(f"Template file not found at {template_path.absolute()}")
            raise HTTPException(
                status_code=500, 
                detail="Template file 'template.docx' not found. Please ensure it exists in the project root."
            )
        
        logger.info("Processing demand letter generation request")
        
        # Prepare context with rich text styling
        context = prepare_context_with_styling(data)
        
        # Load template
        doc = DocxTemplate(str(template_path))
        
        # Configure Jinja2 environment for strict undefined variables
        doc.env = Environment(undefined=StrictUndefined)
        
        # Render the document with styled context
        doc.render(context)
        
        # Save to memory buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        # Generate unique filename for better tracking
        import uuid
        filename = f"demand_letter_{uuid.uuid4().hex[:8]}.docx"
        
        # Create response with proper headers
        response = Response(
            content=buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "X-Generated-Document": filename
            }
        )
        
        logger.info(f"Successfully generated demand letter: {filename}")
        return response
        
    except Exception as e:
        # Enhanced error logging and handling
        error_message = f"Failed to generate letter: {str(e)}"
        logger.error(f"Error in generate_letter: {error_message}", exc_info=True)
        
        # Return appropriate HTTP error
        if "template.docx" in str(e).lower():
            raise HTTPException(status_code=500, detail="Template file error: " + str(e))
        elif "render" in str(e).lower():
            raise HTTPException(status_code=400, detail="Template rendering error: " + str(e))
        else:
            raise HTTPException(status_code=500, detail=error_message)

@app.post("/generate-docx")
async def generate_docx(data: DemandLetterData):
    """Alternative endpoint for n8n and other integrations"""
    return await generate_letter(data)

@app.post("/preview-context")
async def preview_context(data: DemandLetterData):
    """
    Preview the context that would be used for template rendering
    Useful for debugging template variables
    """
    try:
        context = prepare_context_with_styling(data)
        
        # Convert RichText objects to string representations for JSON response
        preview = {}
        for key, value in context.items():
            if isinstance(value, RichText):
                preview[key] = f"[RichText] {str(value)}"
            else:
                preview[key] = str(value)
        
        return {
            "context_preview": preview,
            "total_fields": len(preview),
            "rich_text_fields": sum(1 for v in context.values() if isinstance(v, RichText))
        }
    
    except Exception as e:
        logger.error(f"Error in preview_context: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to preview context: {str(e)}")

# Error handler for better error responses
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {"error": "Internal server error", "detail": "Please check the logs"}

if __name__ == "__main__":
    # Production-ready configuration
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    # Railway and production environment detection
    # is_production = os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("ENVIRONMENT") == "production"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,  # Disable reload in production
        access_log=True,
        log_level="info"
    )
