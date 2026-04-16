# VeriSift/src/verisift/pipeline/text_difference.py

import logging
import difflib
from ..config import VerisiftConfig
# from .sanitizer import ExclusionManager
import re

from diff_match_patch import diff_match_patch

try:
    from sentence_transformers import SentenceTransformer, util
    import torch
    HAS_NLP = True
except ImportError:
    HAS_NLP = False

logger = logging.getLogger(__name__)
_model = None

def get_nlp_model():
    global _model
    if _model is None and HAS_NLP:
        logger.info("Loading AI model for Semantic Analysis...")
        _model = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
    return _model

def _run_literal_comparison(text_a, text_b):
    """Word-to-word logic using SequenceMatcher."""
    matcher = difflib.SequenceMatcher(None, text_a, text_b)
    return matcher.ratio()

def _run_semantic_comparison(text_a, text_b):
    """Intent-based logic using AI embeddings."""
    if not HAS_NLP:
        logger.error("NLP libraries not found. Falling back to Literal mode.")
        return _run_literal_comparison(text_a, text_b)
    
    model = get_nlp_model()
    emb1 = model.encode(text_a, convert_to_tensor=True)
    emb2 = model.encode(text_b, convert_to_tensor=True)
    return util.pytorch_cos_sim(emb1, emb2).item()


def _generate_diff_html(text_expected, text_actual, config: VerisiftConfig, use_semantic=False):
    """
    Core HTML Generator.
    Fixes the double-escaping issue by converting placeholders to HTML after escaping.
    """
    try:
        # --- PHASE 1: CAPTURE ORIGINAL CONTENT ---
        # We use non-greedy matching (.*?) to handle multiple exclusions independently.
        pattern = r'(VERISIFT_START)(.*?)(VERISIFT_END)'
        excl_expected = re.findall(pattern, text_expected)
        excl_actual = re.findall(pattern, text_actual)

        # --- PHASE 2: MASKING FOR THE DIFF ENGINE ---
        # Replace dynamic content with a static token so the engine sees a Match (Flag 0).
        masked_exp = re.sub(pattern, r'\1_MASKED_BLOCK_\3', text_expected)
        masked_act = re.sub(pattern, r'\1_MASKED_BLOCK_\3', text_actual)

        # --- PHASE 3: RUN THE DIFF ENGINE ---

        dmp = diff_match_patch()
        # diffs = dmp.diff_main(text_expected, text_actual)
        diffs = dmp.diff_main(masked_exp, masked_act)
        dmp.diff_cleanupSemantic(diffs)
        
        semantic_matches = set()
        
        if use_semantic and HAS_NLP:
            model = get_nlp_model()
            to_compare_exp, to_compare_act, pair_indices = [], [], []

            for i in range(len(diffs) - 1):
                if diffs[i][0] == -1 and diffs[i+1][0] == 1:
                    # Strip placeholders before semantic AI check to ensure accuracy
                    clean_exp = re.sub(r'VERISIFT_(START|END)', '', diffs[i][1]).strip()
                    clean_act = re.sub(r'VERISIFT_(START|END)', '', diffs[i+1][1]).strip()
                    
                    if len(clean_exp.split()) <= config.semantic_max_phrase and \
                       len(clean_act.split()) <= config.semantic_max_phrase:
                        to_compare_exp.append(clean_exp)
                        to_compare_act.append(clean_act)
                        pair_indices.append(i)

            if to_compare_exp:
                emb_exp = model.encode(to_compare_exp, convert_to_tensor=True)
                emb_act = model.encode(to_compare_act, convert_to_tensor=True)
                scores = torch.nn.functional.cosine_similarity(emb_exp, emb_act)

                for idx, score in enumerate(scores):
                    if score >= config.semantic_threshold:
                        semantic_matches.add(pair_indices[idx])
                        semantic_matches.add(pair_indices[idx] + 1)

        expected_side, actual_side = [], []
        skip_indices = set()

        # Pointers to re-insert the original captured text
        exp_ptr, act_ptr = 0, 0

        for i in range(len(diffs)):
            if i in skip_indices: continue
            flag, data = diffs[i]
            
            # --- STEP 1: SAFETY ESCAPING ---
            clean_data = data.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            
            # --- STEP 2: RE-INSERTION & RENDER ---
            # If the engine found a match for our masked block, we swap the mask for the original text.
            if flag == 0 and "VERISIFT_START_MASKED_BLOCK_VERISIFT_END" in clean_data:
                # We split by the mask to handle cases where text and masks are in the same chunk
                parts = clean_data.split("VERISIFT_START_MASKED_BLOCK_VERISIFT_END")
                
                for j, part in enumerate(parts):
                    if part: # Normal text match
                        expected_side.append(f"<span>{part}</span>")
                        actual_side.append(f"<span>{part}</span>")
                    
                    if j < len(parts) - 1: # Re-insert the original exclusion text
                        orig_exp = excl_expected[exp_ptr][1] if exp_ptr < len(excl_expected) else ""
                        orig_act = excl_actual[act_ptr][1] if act_ptr < len(excl_actual) else ""
                        
                        expected_side.append(f'<span class="diff_excluded">{orig_exp}</span>')
                        actual_side.append(f'<span class="diff_excluded">{orig_act}</span>')
                        
                        exp_ptr += 1
                        act_ptr += 1
                continue

            # --- STEP 3: SEMANTIC & LITERAL FALLBACKS ---
            # Process Semantic, Red (-1), and Green (1) logic as before.
            # Note: If an exclusion is inside a deleted/added block, advance the pointers.
            if flag == -1:
                exp_ptr += data.count("_MASKED_BLOCK_")
                expected_side.append(f'<span class="diff_sub"><em>{clean_data}</em></span>')
                actual_side.append(f'<span style="visibility:hidden">{clean_data}</span>')
            elif flag == 1:
                act_ptr += data.count("_MASKED_BLOCK_")
                expected_side.append(f'<span style="visibility:hidden">{clean_data}</span>')
                actual_side.append(f'<span class="diff_add"><em>{clean_data}</em></span>')
            elif flag == 0:
                expected_side.append(f"<span>{clean_data}</span>")
                actual_side.append(f"<span>{clean_data}</span>")

        return "".join(expected_side), "".join(actual_side)
    except Exception as e:
        logger.error(f"Error generating HTML: {e}")
        return "", ""


def compare_text(text_a: str, text_b: str, config: VerisiftConfig):
    """
    Orchestrator for text diffs.
    Always generates standard literal diff.
    Conditionally generates semantic diff if mode is 'semantic'.
    """
    logger.info(f"Processing text comparison: Mode={config.comparison_mode}")

    if config.ignore_patterns_flag==True and config.ignore_patterns:
        clean_txt_a = re.sub(r'(VERISIFT_START)(.*?)(VERISIFT_END)', '' , text_a, re.IGNORECASE)
        clean_txt_b = re.sub(r'(VERISIFT_START)(.*?)(VERISIFT_END)', '' , text_b, re.IGNORECASE)
        # 1. Scores
        lit_score = _run_literal_comparison(clean_txt_a, clean_txt_b)
        sem_score = _run_semantic_comparison(clean_txt_a, clean_txt_b) if config.comparison_mode == "semantic" else None
    else:
        # 1. Scores
        lit_score = _run_literal_comparison(text_a, text_b)
        sem_score = _run_semantic_comparison(text_a, text_b) if config.comparison_mode == "semantic" else None
    
    # primary_score = sem_score if config.comparison_mode == "semantic" else lit_score

    # 2. ALWAYS generate the Standard Literal HTML (for the main Text Diff tab)
    lit_exp_html, lit_act_html = _generate_diff_html(text_a, text_b, config, use_semantic=False)

    # 3. CONSTRUCT THE RESULT
    result = {
        "text_score": lit_score, #round(lit_score * 100, 2),
        "intent_score": sem_score, #round(sem_score * 100, 2),
        # "literal_score": round(lit_score * 100, 2),
        "is_match": (lit_score ) >= config.text_threshold,
        "expected_diff_html": lit_exp_html,  # Base Text Diff
        "actual_diff_html": lit_act_html,    # Base Text Diff
        "mode_used": config.comparison_mode,
        # Placeholders for semantic HTML
        "semantic_diff_expected_html": None,
        "semantic_diff_actual_html": None
    }

    # 4. Conditionally populate Semantic HTML (for the dedicated Semantic tab)
    if config.comparison_mode == "semantic":
        try:
            logger.info("generating semantic differences...")
            sem_exp_html, sem_act_html = _generate_diff_html(text_a, text_b, config, use_semantic=True)
            result["semantic_diff_expected_html"] = sem_exp_html
            result["semantic_diff_actual_html"] = sem_act_html
            logger.info("generating semantic differences complete...")
        except Exception as e:
            logger.error(f"Error while generating semantic differences......{e}")

    return result