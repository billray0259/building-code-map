import json
import matplotlib.pyplot as plt
from collections import Counter

file = 'data/gracy_3-9.geojson'

with open(file, 'r') as f:
    data = json.load(f)
    
# Pie chart of IRC and IECC codes
features = data["features"]

# Filter out "Unknown" codes
irc_codes = [feat["properties"]["irc"] for feat in features if feat["properties"]["irc"] != "Unknown"]
iecc_codes = [feat["properties"]["iecc"] for feat in features if feat["properties"]["iecc"] != "Unknown"]

irc_count = Counter(irc_codes)
iecc_count = Counter(iecc_codes)

plt.figure()
plt.pie(list(irc_count.values()), labels=[f"{key} ({value})" for key, value in irc_count.items()], autopct='%1.1f%%')
plt.title("Distribution of IRC Codes")
plt.savefig("irc_codes_pie.png")
plt.show()

plt.figure()
plt.pie(list(iecc_count.values()), labels=[f"{key} ({value})" for key, value in iecc_count.items()], autopct='%1.1f%%')
plt.title("Distribution of IECC Codes")
plt.savefig("iecc_codes_pie.png")
plt.show()

# Pie chart of municipalities that are consistent and inconsistent between IRC and IECC codes
consistent = 0
inconsistent = 0
for feat in features:
    irc = feat["properties"]["irc"]
    iecc = feat["properties"]["iecc"]
    if irc == "Unknown" or iecc == "Unknown":
        continue
    if irc == iecc:
        consistent += 1
    else:
        inconsistent += 1

plt.figure()
plt.pie([consistent, inconsistent],
        labels=[f"Consistent ({consistent})", f"Inconsistent ({inconsistent})"],
        autopct='%1.1f%%')
plt.title("Municipalities Consistency between IRC and IECC Codes")
plt.savefig("municipalities_consistency_pie.png")
plt.show()

# Pie chart of Known vs Unknown IRC and IECC codes
known_irc = len(irc_codes)
unknown_irc = len(features) - known_irc

known_iecc = len(iecc_codes)
unknown_iecc = len(features) - known_iecc

plt.figure()
plt.pie([known_irc, unknown_irc],
        labels=[f"Known IRC ({known_irc})", f"Unknown IRC ({unknown_irc})"],
        autopct='%1.1f%%')
plt.title("Known vs Unknown IRC Codes")
plt.savefig("known_vs_unknown_irc_pie.png")
plt.show()

plt.figure()
plt.pie([known_iecc, unknown_iecc],
        labels=[f"Known IECC ({known_iecc})", f"Unknown IECC ({unknown_iecc})"],
        autopct='%1.1f%%')
plt.title("Known vs Unknown IECC Codes")
plt.savefig("known_vs_unknown_iecc_pie.png")
plt.show()