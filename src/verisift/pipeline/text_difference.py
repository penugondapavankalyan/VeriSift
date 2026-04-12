# VeriSift/src/verisift/pipeline/text_difference.py

import logging
import difflib
from ..config import VerisiftConfig

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
    If use_semantic=True: Performs AI synonym pass for Violet highlights.
    If use_semantic=False: Strict Red/Green literal diff.
    """
    try:
        # logger.info("Generating differences...")
        dmp = diff_match_patch()
        diffs = dmp.diff_main(text_expected, text_actual)
        dmp.diff_cleanupSemantic(diffs)
        
        semantic_matches = set()
        # logger.info("Generated diffs.")
        # logger.info("use_semantic is " + str(use_semantic))
        if use_semantic and HAS_NLP:
            model = get_nlp_model()
            to_compare_exp, to_compare_act, pair_indices = [], [], []

            for i in range(len(diffs) - 1):
                if diffs[i][0] == -1 and diffs[i+1][0] == 1:
                    if len(diffs[i][1].split()) <= config.semantic_max_phrase and \
                    len(diffs[i+1][1].split()) <= config.semantic_max_phrase:
                        to_compare_exp.append(diffs[i][1].strip())
                        to_compare_act.append(diffs[i+1][1].strip())
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

        for i in range(len(diffs)):
            if i in skip_indices:
                continue

            flag, data = diffs[i]
            clean_data = data.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            
            # --- 1. THE SEMANTIC PRIORITY ---
            # If this is a deletion that is part of a semantic pair
            if use_semantic and i in semantic_matches and flag == -1:
                match_found = False
                # Look ahead up to 5 chunks to find the corresponding addition
                for j in range(i + 1, min(i + 6, len(diffs))):
                    if j in semantic_matches and diffs[j][0] == 1:
                        partner_data = diffs[j][1].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
                        
                        # Apply Violet to both sides
                        expected_side.append(f'<span class="diff_semantic">{clean_data}</span>')
                        actual_side.append(f'<span class="diff_semantic">{partner_data}</span>')
                        
                        skip_indices.add(j)
                        match_found = True
                        break
                
                if match_found:
                    continue

            # --- 2. THE LITERAL FALLBACK ---
            if flag == 0:  # No change
                tag = f"<span>{clean_data}</span>"
                expected_side.append(tag)
                actual_side.append(tag)
            elif flag == -1:  # True Error / Deletion (Red)
                expected_side.append(f'<span class="diff_sub"><em>{clean_data}</em></span>')
                actual_side.append(f'<span style="visibility:hidden">{clean_data}</span>')
            elif flag == 1:  # True Error / Addition (Green)
                expected_side.append(f'<span style="visibility:hidden">{clean_data}</span>')
                actual_side.append(f'<span class="diff_add"><em>{clean_data}</em></span>')

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