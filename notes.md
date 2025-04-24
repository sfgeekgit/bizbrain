# For version 2.

Features to add later, NOT in current version


### effective_date

Date the document went into effect (such as a contract)

Parse this info from each document itself, probaly with an LLM
Add this data to the document registry and maybe also the document chunks
Maybe this is an optional field in the JSON. Maybe it has a default such as 1977-01-01
When questions are asked, newer documents will always override older ones.
Maybe (Maybe!) there will be a re-ranker that uses this data. Todo: look into that

