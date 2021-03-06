

function GenerateDrop(options = {}) {
	return Diagram([
		AutomaticStack([
			Keyword("DROP"),
			Choice(3, [
				Keyword("FUNCTION"),
				Keyword("INDEX"),
				Keyword("MACRO"),
				Keyword("SCHEMA"),
				Keyword("SEQUENCE"),
				Keyword("TABLE"),
				Keyword("VIEW"),
			]),
			Optional(Sequence([
				Keyword("IF"),
				Keyword("EXISTS")
			]), "skip"),
			GenerateQualifiedTableName(options, "entry-name"),
			Choice(0, [
				new Skip(),
				Keyword("CASCADE"),
				Keyword("RESTRICT")
			])
		])
	])
}

function Initialize(options = {}) {
	document.getElementById("rrdiagram").classList.add("limit-width");
	document.getElementById("rrdiagram").innerHTML = GenerateDrop(options).toString();
}

function Refresh(node_name, set_node) {
	options[node_name] = set_node;
	Initialize(options);
}

options = {}
Initialize()

