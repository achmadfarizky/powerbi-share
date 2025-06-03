import json
import os
import re

# Base name of the PBIP project
pbip_file_name = 'demo/custom_manual'

# Paths
report_path = os.path.join(f"{pbip_file_name}.Report", "report.json")
output_dir = f"{pbip_file_name}_theme_json"

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Load report.json
with open(report_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Utility: extract the 'Value' and convert types appropriately
def extract_value(value):
    if isinstance(value, dict):
        if "expr" in value:
            expr = value["expr"]
            if isinstance(expr, dict) and "Literal" in expr:
                literal = expr["Literal"]
                if isinstance(literal, dict) and "Value" in literal:
                    val = literal["Value"]
                    if isinstance(val, str):
                        val = val.strip("'")  # Remove surrounding single quotes
                        val_lower = val.lower()

                        # Boolean handling
                        if val_lower == "true":
                            return True
                        elif val_lower == "false":
                            return False

                        # Numeric handling
                        if val.endswith("D") or val.endswith("L"):
                            num_str = val[:-1]
                            try:
                                return int(num_str)
                            except ValueError:
                                try:
                                    return float(num_str)
                                except ValueError:
                                    return val  # fallback as string

                        # Fallback for pure float/int strings
                        try:
                            if '.' in val:
                                return float(val)
                            return int(val)
                        except ValueError:
                            return val
                    return val

        # Recursively parse any nested dictionary
        return {k: extract_value(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [extract_value(item) for item in value]

    return value


# Process each section
for section_index, section in enumerate(data.get("sections", [])):
    display_name = section.get("displayName", f"Page_{section_index}")
    visual_containers = section.get("visualContainers", [])

    for vc_index, vc in enumerate(visual_containers):
        config_text = vc.get("config")
        if not config_text:
            continue

        try:
            config = json.loads(config_text)
        except json.JSONDecodeError:
            continue

        single_visual = config.get("singleVisual")
        if not single_visual:
            continue

        visual_type = single_visual.get("visualType", "UnknownType")
        objects = single_visual.get("objects")
        if not objects:
            continue

        # Safe file names
        safe_display_name = re.sub(r'[^\w\-]+', '_', display_name)
        safe_visual_type = re.sub(r'[^\w\-]+', '_', visual_type)

        # === FILE 1: Save raw objects ===
        config_filename = f"config_{safe_display_name}_{vc_index}_{safe_visual_type}.json"
        config_path = os.path.join(output_dir, config_filename)
        with open(config_path, "w", encoding="utf-8") as config_file:
            json.dump(objects, config_file, indent=2)

        # === FILE 2: Save filtered and flattened theme ===
        themed_output = {visual_type: {"*": {}}}  # Only using selector.id = default/missing as "*"

        for key, items in objects.items():
            for item in items:
                raw_selector_id = item.get("selector", {}).get("id")

                # Only keep selector.id == default or None
                if raw_selector_id not in (None, "default"):
                    continue  # skip other selectors

                flat_properties = {
                    prop_key: extract_value(prop_val)
                    for prop_key, prop_val in item.get("properties", {}).items()
                }

                if key not in themed_output[visual_type]["*"]:
                    themed_output[visual_type]["*"][key] = []

                if flat_properties not in themed_output[visual_type]["*"][key]:
                    themed_output[visual_type]["*"][key].append(flat_properties)

        # Wrap with static parent 'visualStyles'
        final_output = {
            "visualStyles": themed_output
        }

        # Write theme JSON
        theme_filename = f"theme_{safe_display_name}_{vc_index}_{safe_visual_type}.json"
        theme_path = os.path.join(output_dir, theme_filename)
        with open(theme_path, "w", encoding="utf-8") as theme_file:
            json.dump(final_output, theme_file, indent=2)

        print(f"Saved: {config_filename} and {theme_filename} to {output_dir}")
