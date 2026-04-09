# # VeriSift/src/verisift/pipeline/text_diff.py
# import logging
# import difflib
# from ..config import VeridocConfig

# # Import the heavy AI stuff if we absolutely have to keep the 'Literal' mode fast and lightweight.
# try:
#     from sentence_transformers import SentenceTransformer, util
#     HAS_NLP = True
# except ImportError:
#     HAS_NLP = False

# logger = logging.getLogger(__name__)
# _model = None

# def get_nlp_model():
#     global _model
#     if _model is None and HAS_NLP:
#         logger.info("Loading AI model for Semantic Analysis...")
#         _model = SentenceTransformer('all-MiniLM-L6-v2')
#     return _model

# def _run_literal_comparison(text_a, text_b):
#     """Word-to-word logic using SequenceMatcher."""
#     matcher = difflib.SequenceMatcher(None, text_a, text_b)
#     return matcher.ratio()

# def _run_semantic_comparison(text_a, text_b):
#     """Intent-based logic using AI embeddings."""
#     if not HAS_NLP:
#         logger.error("NLP libraries not found. Falling back to Literal mode.")
#         return _run_literal_comparison(text_a, text_b)
    
#     model = get_nlp_model()
#     emb1 = model.encode(text_a, convert_to_tensor=True)
#     emb2 = model.encode(text_b, convert_to_tensor=True)
#     return util.pytorch_cos_sim(emb1, emb2).item()

# def compare_text(text_a: str, text_b: str, config: VeridocConfig):
#     """
#     Detailed Explanation:
#     The Router. It checks the config and decides which engine to fire up.
#     """
#     logger.info(f"Running text analysis in '{config.comparison_mode}' mode.")

#     # 1. Routing Logic
#     if config.comparison_mode == "semantic":
#         score = _run_semantic_comparison(text_a, text_b)
#     else:
#         score = _run_literal_comparison(text_a, text_b)

#     # 2. Shared Logic (The Visual Diff)
#     # # Regardless of the score, the user always wants to see the +/- diff.
#     # diff_generator = difflib.ndiff(text_a.splitlines(), text_b.splitlines())

#     # We use HtmlDiff to create the 2-column table seen in professional reports


# # ----------------------------------------------------------------------------------------------------

#     # from diff_match_patch import diff_match_patch

#     # def get_test_diff(expected_text, actual_text):
#     #     dmp = diff_match_patch()
        
#     #     # 1. Generate the diffs
#     #     diffs = dmp.diff_main(expected_text, actual_text)
        
#     #     # 2. Crucial: This groups small changes together and handles shifts
#     #     dmp.diff_cleanupSemantic(diffs)
        
#     #     # 3. Convert to HTML
#     #     return diffs
    
#     # def diff_to_custom_html(diffs):
#     #     """
#     #     Converts DMP output into a format compatible with your 
#     #     existing Veridoc report template.
#     #     """
#     #     html_output = []
#     #     for (flag, data) in diffs:
#     #         # Escape HTML characters to prevent XSS or broken tags
#     #         text = data.replace('&', '&amp;').replace('<', '&lt;') \
#     #                 .replace('>', '&gt;').replace('\n', '<br>')
            
#     #         if flag == 0: # EQUAL
#     #             html_output.append(f'<span>{text}</span>')
#     #         elif flag == 1: # INSERT (Actual)
#     #             html_output.append(f'<span class="diff_add"><em>{text}</em></span>')
#     #         elif flag == -1: # DELETE (Expected)
#     #             html_output.append(f'<span class="diff_sub"><em>{text}</em></span>')
                
#     #     return "".join(html_output)
    
#     # test_ans = diff_to_custom_html(get_test_diff(text_b, text_a))
#     # try:
#     #     with open(r"C:\Users\PenugondaPavanKalyan\Downloads\veridoc\sample_test_googl.html", "w") as tst_html_file:
#     #         tst_html_file.write(test_ans)
#     # except Exception as e:
#     #     print(f"{e} while opening html file")




# # ----------------------------------------------------------------------------------------------------



#     hd = difflib.HtmlDiff(tabsize=4)
    
#     # make_table returns only the <table> section, perfect for embedding
#     diff_table = hd.make_table(
#         text_a.splitlines(), 
#         text_b.splitlines(), 
#         fromdesc="Expected", 
#         todesc="Actual",
#         context=False, 
#         numlines=3
#     )
    
#     diff_table = diff_table.replace("#@#@#@#@#", "<br>")
#     return {
#         "score": round(score, 4),
#         "is_match": score >= config.text_threshold,
#         # "diff_text": "\n".join(diff_generator),
#         # "diff_text": diff_table,
#         "diff_text": diff_table,
#         "mode_used": config.comparison_mode
#     }