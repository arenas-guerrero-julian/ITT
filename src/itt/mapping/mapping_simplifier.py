import pandas as pd
from lark import Lark
from lark import Transformer
from random import randint
from uuid import uuid4

# IRIREF is different
# noinspection PyInterpreter
sparql_grammar = r"""

    queryunit                 : query

    query                     : prologue ( selectquery | constructquery | describequery | askquery ) valuesclause

    updateunit                : update

    prologue                  : ( basedecl | prefixdecl )*

    basedecl                  : "BASE"i IRIREF

    prefixdecl                : "PREFIX"i PNAME_NS IRIREF

    selectquery               : selectclause datasetclause* whereclause solutionmodifier

    subselect                 : selectclause whereclause solutionmodifier valuesclause

    selectclause              : "SELECT"i ( DISTINCT | REDUCED )? ( ( var | ( "(" expression "AS"i var ")" ) )+ | "*" )

    constructquery            : "CONSTRUCT"i ( constructtemplate datasetclause* whereclause solutionmodifier | datasetclause* "WHERE"i "{" triplestemplate? "}" solutionmodifier )

    describequery             : "DESCRIBE"i ( varoriri+ | "*" ) datasetclause* whereclause? solutionmodifier

    askquery                  : "ASK"i datasetclause* whereclause solutionmodifier

    datasetclause             : "FROM"i ( defaultgraphclause | namedgraphclause )

    defaultgraphclause        : sourceselector

    namedgraphclause          : "NAMED"i sourceselector

    sourceselector            : iri

    whereclause               : "WHERE"i? groupgraphpattern

    solutionmodifier          : groupclause? havingclause? orderclause? limitoffsetclauses?

    groupclause               : "GROUP"i "BY"i groupcondition+

    groupcondition            : builtincall | functioncall | "(" expression ( "AS"i var )? ")" | var

    havingclause              : "HAVING"i havingcondition+

    havingcondition           : constraint

    orderclause               : "ORDER"i "BY"i ordercondition+

    ordercondition            : ( ( ASC | DESC ) brackettedexpression ) | ( constraint | var )

    limitoffsetclauses        : limitclause offsetclause? | offsetclause limitclause?

    limitclause               : "LIMIT"i INTEGER

    offsetclause              : "OFFSET"i INTEGER

    valuesclause              : ( "VALUES"i datablock )?

    update                    : prologue ( update1 ( ";" update )? )?

    update1                   : load | clear | drop | add | move | copy | create | insertdata | deletedata | deletewhere | modify

    load                      : "LOAD"i SILENT? iri ( "INTO"i graphref )?

    clear                     : "CLEAR"i SILENT? graphrefall

    drop                      : "DROP"i SILENT? graphrefall

    create                    : "CREATE"i SILENT? graphref

    add                       : "ADD"i SILENT? graphordefault "TO"i graphordefault

    move                      : "MOVE"i SILENT? graphordefault "TO"i graphordefault

    copy                      : "COPY"i SILENT? graphordefault "TO"i graphordefault

    insertdata                : "INSERT"i "DATA"i quaddata

    deletedata                : "DELETE"i "DATA"i quaddata

    deletewhere               : "DELETE"i "WHERE"i quadpattern

    modify                    : ( WITH iri )? ( deleteclause insertclause? | insertclause ) usingclause* "WHERE"i groupgraphpattern

    deleteclause              : "DELETE"i quadpattern

    insertclause              : "INSERT"i quadpattern

    usingclause               : "USING"i ( iri | "NAMED"i iri )

    graphordefault            : "DEFAULT"i | "GRAPH"i? iri

    graphref                  : "GRAPH"i iri

    graphrefall               : graphref | DEFAULT | NAMED | ALL

    quadpattern               : "{" quads "}"

    quaddata                  : "{" quads "}"

    quads                     : triplestemplate? ( quadsnottriples "."? triplestemplate? )*

    quadsnottriples           : "GRAPH"i varoriri "{" triplestemplate? "}"

    triplestemplate           : triplessamesubject ( "." triplestemplate? )?

    groupgraphpattern         : "{" ( subselect | groupgraphpatternsub ) "}"

    groupgraphpatternsub      : triplesblock? ( graphpatternnottriples "."? triplesblock? )*

    triplesblock              : triplessamesubjectpath ( "." triplesblock? )?

    graphpatternnottriples    : grouporuniongraphpattern | optionalgraphpattern | minusgraphpattern | graphgraphpattern | servicegraphpattern | filter | bind | inlinedata

    optionalgraphpattern      : "OPTIONAL"i groupgraphpattern

    graphgraphpattern         : "GRAPH"i varoriri groupgraphpattern

    servicegraphpattern       : "SERVICE"i SILENT? varoriri groupgraphpattern

    bind                      : "BIND"i "(" expression "AS"i var ")"

    inlinedata                : "VALUES"i datablock

    datablock                 : inlinedataonevar | inlinedatafull

    inlinedataonevar          : var "{" datablockvalue* "}"

    inlinedatafull            : ( NIL | "(" var* ")" ) "{" ( "(" datablockvalue* ")" | NIL )* "}"

    datablockvalue            : iri | rdfliteral | numericliteral | booleanliteral | "UNDEF"

    minusgraphpattern         : "MINUS"i groupgraphpattern

    grouporuniongraphpattern  : groupgraphpattern ( "UNION"i groupgraphpattern )*

    filter                    : "FILTER"i constraint

    constraint                : brackettedexpression | builtincall | functioncall

    functioncall              : iri arglist

    arglist                   : NIL | "(" DISTINCT? expression ( "," expression )* ")"

    expressionlist            : NIL | "(" expression ( "," expression )* ")"

    constructtemplate         : "{" constructtriples? "}"

    constructtriples          : triplessamesubject ( "." constructtriples? )?

    triplessamesubject        : varorterm propertylistnotempty | triplesnode propertylist

    propertylist              : propertylistnotempty?

    propertylistnotempty      : verb objectlist ( ";" ( verb objectlist )? )*

    verb                      : varoriri | A_RDF_TYPE

    objectlist                : object ( "," object )*

    object                    : graphnode

    triplessamesubjectpath    : varorterm propertylistpathnotempty | triplesnodepath propertylistpath

    propertylistpath          : propertylistpathnotempty?

    propertylistpathnotempty  : ( verbpath | verbsimple ) objectlistpath ( ";" ( ( verbpath | verbsimple ) objectlist )? )*

    verbpath                  : path

    verbsimple                : var

    objectlistpath            : objectpath ( "," objectpath )*

    objectpath                : graphnodepath

    path                      : pathalternative

    pathalternative           : pathsequence ( "|" pathsequence )*

    pathsequence              : patheltorinverse ( "/" patheltorinverse )*

    pathelt                   : pathprimary pathmod?

    patheltorinverse          : pathelt | "^" pathelt

    pathmod                   : "?" | "*" | "+"

    pathprimary               : iri | A_RDF_TYPE | "!" pathnegatedpropertyset | "(" path ")"

    pathnegatedpropertyset    : pathoneinpropertyset | "(" ( pathoneinpropertyset ( "|" pathoneinpropertyset )* )? ")"

    pathoneinpropertyset      : iri | A_RDF_TYPE | "^" ( iri | A_RDF_TYPE )

    integer                   : INTEGER

    triplesnode               : collection | blanknodepropertylist

    blanknodepropertylist     : "[" propertylistnotempty "]"

    triplesnodepath           : collectionpath | blanknodepropertylistpath

    blanknodepropertylistpath : "[" propertylistpathnotempty "]"

    collection                : "(" graphnode+ ")"

    collectionpath            : "(" graphnodepath+ ")"

    graphnode                 : varorterm | triplesnode

    graphnodepath             : varorterm | triplesnodepath

    varorterm                 : var | graphterm

    varoriri                  : var | iri

    var                       : VAR1 | VAR2

    graphterm                 : iri | rdfliteral | numericliteral | booleanliteral | blanknode | NIL

    expression                : conditionalorexpression

    conditionalorexpression   : conditionalandexpression ( "||" conditionalandexpression )*

    conditionalandexpression  : valuelogical ( "&&" valuelogical )*

    valuelogical              : relationalexpression

    relationalexpression      : numericexpression ( equal | not_equal | lower | greater | lower_equal | greater_equal | is_in | is_not_in )?

    equal                     : "=" numericexpression

    not_equal                 : "!=" numericexpression

    lower                     : "<" numericexpression

    greater                   : ">" numericexpression

    lower_equal               : "<=" numericexpression

    greater_equal             : ">=" numericexpression

    is_in                     : "IN"i numericexpression

    is_not_in                 : "NOT"i "IN"i expressionlist

    numericexpression         : additiveexpression

    additiveexpression        : multiplicativeexpression ( "+" multiplicativeexpression | "-" multiplicativeexpression | ( numericliteralpositive | numericliteralnegative ) ( ( "*" unaryexpression ) | ( "/" unaryexpression ) )* )*

    multiplicativeexpression  : unaryexpression ( "*" unaryexpression | "/" unaryexpression )*

    unaryexpression           : "!" primaryexpression | "+" primaryexpression | "-" primaryexpression | primaryexpression

    primaryexpression         : brackettedexpression | builtincall | iri | functioncall | rdfliteral | numericliteral | booleanliteral | var

    brackettedexpression      : "(" expression ")"

    builtincall               : aggregate
                              | STR "(" expression ")"
                              | LANG "(" expression ")"
                              | LANGMATCHES "(" expression "," expression ")"
                              | DATATYPE "(" expression ")"
                              | BOUND "(" var ")"
                              | IRI "(" expression ")"
                              | URI "(" expression ")"
                              | BNODE ( "(" expression ")" | NIL )
                              | RAND NIL
                              | ABS "(" expression ")"
                              | CEIL "(" expression ")"
                              | FLOOR "(" expression ")"
                              | ROUND "(" expression ")"
                              | CONCAT expressionlist
                              | substringexpression
                              | STRLEN "(" expression ")"
                              | strreplaceexpression
                              | UCASE "(" expression ")"
                              | LCASE "(" expression ")"
                              | ENCODE_FOR_URI "(" expression ")"
                              | CONTAINS "(" expression "," expression ")"
                              | STRSTARTS "(" expression "," expression ")"
                              | STRENDS "(" expression "," expression ")"
                              | STRBEFORE "(" expression "," expression ")"
                              | STRAFTER "(" expression "," expression ")"
                              | YEAR "(" expression ")"
                              | MONTH "(" expression ")"
                              | DAY "(" expression ")"
                              | HOURS "(" expression ")"
                              | MINUTES "(" expression ")"
                              | SECONDS "(" expression ")"
                              | TIMEZONE "(" expression ")"
                              | TZ "(" expression ")"
                              | NOW NIL
                              | UUID NIL
                              | STRUUID NIL
                              | MD5 "(" expression ")"
                              | SHA1 "(" expression ")"
                              | SHA256 "(" expression ")"
                              | SHA384 "(" expression ")"
                              | SHA512 "(" expression ")"
                              | COALESCE expressionlist
                              | IF "(" expression "," expression "," expression ")"
                              | STRLANG "(" expression "," expression ")"
                              | STRDT "(" expression "," expression ")"
                              | SAMETERM "(" expression "," expression ")"
                              | ISIRI "(" expression ")"
                              | ISURI "(" expression ")"
                              | ISBLANK "(" expression ")"
                              | ISLITERAL "(" expression ")"
                              | ISNUMERIC "(" expression ")"
                              | regexexpression
                              | existsfunc
                              | notexistsfunc

    regexexpression           : "REGEX"i "(" expression "," expression ( "," expression )? ")"

    substringexpression       : "SUBSTR"i "(" expression "," expression ( "," expression )? ")"

    strreplaceexpression      : "REPLACE"i "(" expression "," expression "," expression ( "," expression )? ")"

    existsfunc                : "EXISTS"i groupgraphpattern

    notexistsfunc             : "NOT"i "EXISTS"i groupgraphpattern

    aggregate                 : COUNT "(" DISTINCT? ( "*" | expression ) ")"
                              | SUM "(" DISTINCT? expression ")"
                              | MIN "(" DISTINCT? expression ")"
                              | MAX "(" DISTINCT? expression ")"
                              | AVG "(" DISTINCT? expression ")"
                              | SAMPLE "(" DISTINCT? expression ")"
                              | GROUP_CONCAT "(" DISTINCT? expression ( ";" "SEPARATOR"i "=" string )? ")"

    rdfliteral                : string ( LANGTAG | ( "^^" iri ) )?

    numericliteral            : numericliteralunsigned | numericliteralpositive | numericliteralnegative

    numericliteralunsigned    : INTEGER | DECIMAL | DOUBLE

    numericliteralpositive    : INTEGER_POSITIVE | DECIMAL_POSITIVE | DOUBLE_POSITIVE

    numericliteralnegative    : INTEGER_NEGATIVE | DECIMAL_NEGATIVE | DOUBLE_NEGATIVE

    booleanliteral            : TRUE | FALSE

    string                    : STRING_LITERAL1 | STRING_LITERAL2 | STRING_LITERAL_LONG1 | STRING_LITERAL_LONG2

    iri                       : IRIREF | prefixedname

    prefixedname              : PNAME_LN | PNAME_NS

    blanknode                 : BLANK_NODE_LABEL | ANON

    IRIREF                    : "<" /([^<>"{}|\s])*/ ">"

    PNAME_NS                  : PN_PREFIX? ":"

    PNAME_LN                  : PNAME_NS PN_LOCAL

    BLANK_NODE_LABEL          : "_:" ( PN_CHARS_U | /[0-9]/ ) ((PN_CHARS|".")* PN_CHARS)?

    VAR1                      : "?" VARNAME

    VAR2                      : "$" VARNAME

    LANGTAG                   : "@" /[a-zA-Z]+/ ("-" /[a-zA-Z0-9]+/)*

    INTEGER                   : /[0-9]+/

    DECIMAL                   : /[0-9]*/ "." /[0-9]+/

    DOUBLE                    : /[0-9]+/ "." /[0-9]*/ EXPONENT | "." (/[0-9]/)+ EXPONENT | (/[0-9]/)+ EXPONENT

    INTEGER_POSITIVE          : "+" INTEGER

    DECIMAL_POSITIVE          : "+" DECIMAL

    DOUBLE_POSITIVE           : "+" DOUBLE

    INTEGER_NEGATIVE          : "-" INTEGER

    DECIMAL_NEGATIVE          : "-" DECIMAL

    DOUBLE_NEGATIVE           : "-" DOUBLE

    EXPONENT                  : /[eE]/ /[+-]?/ /[0-9]+/

    STRING_LITERAL1           : "'" ( (/[^\u0027\u005C\u000A\u000D]/) | ECHAR )* "'"

    STRING_LITERAL2           : "\"" ( (/[^\u0022\u005C\u000A\u000D]/) | ECHAR )* "\""

    STRING_LITERAL_LONG1      : "'''" ( ( "'" | "''" )? ( /[^'\\]/ | ECHAR ) )* "'''"

    STRING_LITERAL_LONG2      : "\"\"\"" ( ( "\"" | "\"\"" )? ( /[^"\\]/ | ECHAR ) )* "\"\"\""

    ECHAR                     : "\"" /[tbnrf\"']/

    NIL                       : "(" WS* ")"

    WS                        : /\u0020/ | /\u0009/ | /\u000D/ | /\u000A/

    ANON                      : "[" WS* "]"

    PN_CHARS_BASE             : /[A-Z]/ | /[a-z]/ | /[\u00C0-\u00D6]/ | /[\u00D8-\u00F6]/ | /[\u00F8-\u02FF]/ | /[\u0370-\u037D]/ | /[\u037F-\u1FFF]/ | /[\u200C-\u200D]/ | /[\u2070-\u218F]/ | /[\u2C00-\u2FEF]/ | /[\u3001-\uD7FF]/ | /[\uF900-\uFDCF]/ | /[\uFDF0-\uFFFD]/

    PN_CHARS_U                : PN_CHARS_BASE | "_"

    VARNAME                   : ( PN_CHARS_U | /[0-9]/ ) ( PN_CHARS_U | /[0-9]/ | /\u00B7/ | /[\u0300-\u036F]/ | /[\u203F-\u2040]/ )*

    PN_CHARS                  : PN_CHARS_U | "-" | /[0-9]/ | /\u00B7/ | /[\u0300-\u036F]/ | /[\u203F-\u2040]/

    PN_PREFIX                 : PN_CHARS_BASE ((PN_CHARS|".")* PN_CHARS)?

    PN_LOCAL                  : (PN_CHARS_U | ":" | /[0-9]/ | PLX ) ((PN_CHARS | "." | ":" | PLX)* (PN_CHARS | ":" | PLX) )?

    PLX                       : PERCENT | PN_LOCAL_ESC

    PERCENT                   : "%" HEX HEX

    HEX                       : /[0-9]/ | /[A-F]/ | /[a-f]/

    PN_LOCAL_ESC              : "\\" ( "_" | "~" | "." | "-" | "!" | "$" | "&" | "'" | "(" | ")" | "*" | "+" | "," | ";" | "=" | "/" | "?" | "#" | "@" | "%" )

    TRUE                      : "true"i

    FALSE                     : "false"i

    A_RDF_TYPE                : "a"

    DISTINCT                  : "DISTINCT"i

    REDUCED                   : "REDUCED"i

    SILENT                    : "SILENT"i

    COUNT                     : "COUNT"i

    SUM                       : "SUM"i

    MIN                       : "MIN"i

    MAX                       : "MAX"i

    AVG                       : "AVG"i

    SAMPLE                    : "SAMPLE"i

    GROUP_CONCAT              : "GROUP_CONCAT"i

    STR                       : "STR"i

    LANG                      : "LANG"i

    LANGMATCHES               : "LANGMATCHES"i

    DATATYPE                  : "DATATYPE"i

    BOUND                     : "BOUND"i

    IRI                       : "IRI"i

    URI                       : "URI"i

    BNODE                     : "BNODE"i

    RAND                      : "RAND"i

    ABS                       : "ABS"i

    CEIL                      : "CEIL"i

    FLOOR                     : "FLOOR"i

    ROUND                     : "ROUND"i

    CONCAT                    : "CONCAT"i

    STRLEN                    : "STRLEN"i

    UCASE                     : "UCASE"i

    LCASE                     : "LCASE"i

    ENCODE_FOR_URI            : "ENCODE_FOR_URI"i

    CONTAINS                  : "CONTAINS"i

    STRSTARTS                 : "STRSTARTS"i

    STRENDS                   : "STRENDS"i

    STRBEFORE                 : "STRBEFORE"i

    STRAFTER                  : "STRAFTER"i

    YEAR                      : "YEAR"i

    MONTH                     : "MONTH"i

    DAY                       : "DAY"i

    HOURS                     : "HOURS"i

    MINUTES                   : "MINUTES"i

    SECONDS                   : "SECONDS"i

    TIMEZONE                  : "TIMEZONE"i

    TZ                        : "TZ"i

    NOW                       : "NOW"i

    UUID                      : "UUID"i

    STRUUID                   : "STRUUID"i

    MD5                       : "MD5"i

    SHA1                      : "SHA1"i

    SHA256                    : "SHA256"i

    SHA384                    : "SHA384"i

    SHA512                    : "SHA512"i

    COALESCE                  : "COALESCE"i

    IF                        : "IF"i

    STRLANG                   : "STRLANG"i

    STRDT                     : "STRDT"i

    SAMETERM                  : "sameTerm"i

    ISIRI                     : "isIRI"i

    ISURI                     : "isURI"i

    ISBLANK                   : "isBLANK"i

    ISLITERAL                 : "isLITERAL"i

    ISNUMERIC                 : "isNUMERIC"i

    DEFAULT                   : "DEFAULT"i

    NAMED                     : "NAMED"i

    ALL                       : "ALL"i

    ASC                       : "ASC"i

    DESC                      : "DESC"i

    WITH                      : "WITH"i

    %import common.WS         -> LARKWS
    %ignore LARKWS

    """


class TreeToSPARQL(Transformer):

    def rdfliteral(self, s):
        if len(s) == 1:
            # literal only with lexical form
            (s,) = s
            f'{s}'
        elif s[1][0] == 'langtag':
            # literal with langtag
            s = f'{s[0]}{s[1][1]}'
        else:
            # literal with datatype
            s = f'{s[0]}^^{s[1][1]}'

        return 'literal', s

    def string(self, s):
        (s,) = s
        return s

    def A_RDF_TYPE(self, s):
        return 'iriref', '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>'

    def STRING_LITERAL1(self, s):
        return f'"{s[1:-1]}"'

    def STRING_LITERAL2(self, s):
        return f'{s}'

    def STRING_LITERAL_LONG1(self, s):
        # TODO: all strings, blanknodes... mmust be processed
        return f'"{s[3:-3]}"'

    def STRING_LITERAL_LONG2(self, s):
        return f'"{s[3:-3]}"'

    def IRIREF(self, s):
        return 'iriref', f'{s}'

    def ANON(self, s):
        return f'_:b{uuid4().hex}'

    def TRUE(self, s):
        return '"true"^^<http://www.w3.org/2001/XMLSchema#boolean>'

    def FALSE(self, s):
        return '"false"^^<http://www.w3.org/2001/XMLSchema#boolean>'

    def BLANK_NODE_LABEL(self, s):
        return f'{s}'

    def blanknode(self, s):
        (s,) = s
        return 'blanknode', f'{s}'

    def INTEGER(self, s):
        return f'"{s}"^^<http://www.w3.org/2001/XMLSchema#integer>'

    def DECIMAL(self, s):
        return f'"{float(s)}"^^<http://www.w3.org/2001/XMLSchema#decimal>'

    def DOUBLE(self, s):

        return f'"{float(s)}"^^<http://www.w3.org/2001/XMLSchema#double>'

    def LANGTAG(self, s):
        return 'langtag', f'{s.lower()}'

    def prefixedname(self, s):
        (s,) = s
        return s

    def PNAME_LN(self, s):
        return 'prefixed_name', f'{s}'

    def PNAME_NS(self, s):
        return 'prefixed_name', f'{s[:-1]}'

    def var(self, s):
        (s,) = s
        return 'var', s[1:]

    def graphterm(self, s):
        (s,) = s
        return s

    def varorterm(self, s):
        (s,) = s
        return s

    def graphnode(self, s):
        (s,) = s
        return s

    def iri(self, s):
        (s,) = s
        return s

    def graphnodepath(self, s):
        (s,) = s
        return s

    def objectpath(self, s):
        (s,) = s
        return s

    def object(self, s):
        (s,) = s
        return s

    def objectlistpath(self, s):
        return s

    def objectlist(self, s):
        return s

    def path(self, s):
        (s,) = s
        return s

    def verbpath(self, s):
        (s,) = s
        return s

    def numericliteralunsigned(self, s):
        (s,) = s
        return s

    def numericliteral(self, s):
        (s,) = s
        return 'numeric_literal', s

    def booleanliteral(self, s):
        (s,) = s
        return 'boolean_literal', s

    def pathalternative(self, s):
        (s,) = s
        return s

    def pathprimary(self, s):
        (s,) = s
        return s

    def verbsimple(self, s):
        (s,) = s
        return s

    def pathelt(self, s):
        (s,) = s
        return s

    def patheltorinverse(self, s):
        (s,) = s
        return s

    def pathsequence(self, s):
        (s,) = s
        return s

    def propertylistpathnotempty(self, s):
        p_list = s[::2]
        o_list = s[1::2]

        return list(zip(p_list, o_list))

    def propertylistpath(self, s):
        return s

    def blanknodepropertylistpath(self, s):
        return s[0][0]

    def triplesnodepath(self, s):
        return s

    def triplessamesubjectpath(self, s):
        # TriplesSameSubjectPath ::= VarOrTerm PropertyListPathNotEmpty | TriplesNodePath PropertyListPath

        s, l, = s
        if not l:
            # TriplesNodePath PropertyListPath
            return ('blanknode', f'_:b{uuid4().hex}'), s
        else:
            # VarOrTerm PropertyListPathNotEmpty
            return s, l

    def primaryexpression(self, s):
        (s,) = s
        return s

    def unaryexpression(self, s):
        (s,) = s
        return s

    def multiplicativeexpression(self, s):
        (s,) = s
        return s

    def additiveexpression(self, s):
        (s,) = s
        return s

    def numericexpression(self, s):
        (s,) = s
        return s

    def arglist(self, s):
        return s

    def relationalexpression(self, s):
        if len(s) == 1:
            (s,) = s
            return s
        elif len(s) == 2:
            return s[1][0], s[0], s[1][1]
        else:
            raise

    def functioncall(self, s):
        return 'functioncall', s[0], s[1]

    def builtincall(self, s):
        return 'builtincall', s

    def equal(self, s):
        (s,) = s
        return '=', s

    def not_equal(self, s):
        (s,) = s
        return '!=', (s[0], s[1])

    def lower(self, s):
        (s,) = s
        return '<', (s[0], s[1])

    def greater(self, s):
        (s,) = s
        return '>', (s[0], s[1])

    def lower_equal(self, s):
        (s,) = s
        return '<=', (s[0], s[1])

    def greater_equal(self, s):
        (s,) = s
        return '>=', (s[0], s[1])

    def is_in(self, s):
        (s,) = s
        return 'IN', (s[0], s[1])

    def is_not_in(self, s):
        (s,) = s
        return 'NOT IN', (s[0], s[1])

    def valuelogical(self, s):
        (s,) = s
        return s

    def conditionalandexpression(self, s):
        if len(s) == 1:
            return s[0]
        else:
            return '&&', s

    def conditionalorexpression(self, s):
        if len(s) == 1:
            return s[0]
        else:
            return '||', s

    def brackettedexpression(self, s):
        (s,) = s
        return s

    def expression(self, s):
        (s,) = s
        return s

    def constraint(self, s):
        (s,) = s
        return s

    def graphpatternnottriples(self, s):
        (s,) = s
        return s

    def regexexpression(self, s):
        # flags defined at  http://www.w3.org/TR/xpath-functions/#flags
        text = s[0][1]
        pattern = s[1][1][1:-1]

        if len(s) == 2:
            # no FLAG provided
            flags = ''
            return 'regex', text, pattern, flags
        elif len(s) == 3:
            flags = s[2][1][1:-1]
            if flags not in ['s', 'm', 'i', 'x', 'q']:
                raise ValueError(
                    'err:FORX0001, Invalid regular expression flags. Raised by regular expression functions such as fn:matches and fn:replace if the regular expression flags contain a character other than i, m, q, s, or x. ')
            return 'regex', text, pattern, flags
        else:
            raise

    def substringexpression(self, s):
        source = s[0][1]
        startingLoc = s[1][1][1:-45]

        if len(s) == 2:
            # no FLAG provided
            length = ''
            return 'substr', source, startingLoc, length
        elif len(s) == 3:
            length = s[2][1][1:-45]
            return 'substr', source, startingLoc, length
        else:
            raise

    def strreplaceexpression(self, s):
        # flags defined at  http://www.w3.org/TR/xpath-functions/#flags
        arg = s[0][1]
        pattern = s[1][1][1:-1]
        replacement = s[2][1:-1]

        if len(s) == 3:
            # no FLAG provided
            flags = ''
            return 'replace', arg, pattern, replacement, flags
        elif len(s) == 4:
            flags = s[3][1][1:-1]
            if flags not in ['s', 'm', 'i', 'x', 'q']:
                raise ValueError(
                    'err:FORX0001, Invalid regular expression flags. Raised by regular expression functions such as fn:matches and fn:replace if the regular expression flags contain a character other than i, m, q, s, or x. ')
            return 'replace', arg, pattern, replacement, flags
        else:
            raise

    def existsfunc(self, s):
        return 'EXISTS', s[0]

    def notexistsfunc(self, s):
        return 'NOT EXISTS', s[0]

    def aggregate(self, s):
        return 'aggregate', s

    def MIN(self, s):
        return 'MIN'

    def GROUP_CONCAT(self, s):
        return 'GROUP_CONCAT'

    def DISTINCT(self, s):
        return 'DISTINCT'

    def prefixdecl(self, s):
        return s[0][1], s[1][1][1:-1]

    def basedecl(self, s):
        return '', s[0][1][1:-1]

    def query(self, s):
        return 'query', s


def build_triple_pattern_query(triplesblock, triple_patterns, bgp):
    project_vars = set()

    s = triplesblock[0]
    for pred_block in triplesblock[1]:
        p = pred_block[0]
        for obj_block in pred_block[1]:
            o = obj_block

            tp = []
            if s[0] == 'var':
                tp.append(f"?{s[1]}")
            else:
                tp.append(s[1])
            if p[0] == 'var':
                tp.append(f"?{p[1]}")
            else:
                tp.append(p[1])
            if o[0] == 'var':
                tp.append(f"?{o[1]}")
            else:
                tp.append(o[1])
            tp.append(bgp)
            triple_patterns.append(tp)

    tp_query = 'SELECT '

    if s[0] == 'var':
        tp_query += f's AS {s[1]}, '
        project_vars.add(s[1])
    if p[0] == 'var':
        tp_query += f'p AS {p[1]}, '
        project_vars.add(p[1])
    if o[0] == 'var':
        tp_query += f'o AS {o[1]} '
        project_vars.add(o[1])

    tp_query = f'{tp_query[:-2]} ' if tp_query.endswith(', ') else tp_query

    tp_query += "FROM triple_table_df "

    if s[0] != 'var' or p[0] != 'var' or o[0] != 'var':
        tp_query += 'WHERE '

        if s[0] == 'prefixed_name':
            tp_query += f"s='<{s[1]}>'"
        elif s[0] != 'var':
            tp_query += f"s='{s[1]}' AND "

        if p[0] == 'prefixed_name':
            tp_query += f"p='<{p[1]}>'"
        elif p[0] != 'var':
            tp_query += f"p='{p[1]}' AND "

        if o[0] == 'prefixed_name':
            tp_query += f"o='<{o[1]}>'"
        elif o[0] != 'var':
            tp_query += f"o='{o[1]}'"

        if tp_query.endswith(' AND '):
            tp_query = tp_query[:-5]

    return tp_query, project_vars, triple_patterns


def build_filter_selection(filter):
    return ''


def process_rule(rule, project_vars, views_project_vars=dict(), sql_query='', triple_patterns=list(), bgp=''):
    view_alias = f'v{randint(0, 1000000)}'

    if rule.data == 'groupgraphpattern':
        bgp = f'bgp{randint(0, 1000000)}'
        for child in rule.children:
            sql_query, view_alias, project_vars, triple_patterns = process_rule(child, project_vars, views_project_vars, sql_query, triple_patterns, bgp)

    elif rule.data == 'groupgraphpatternsub':
        for child in rule.children:
            sql_query, view_alias, project_vars, triple_patterns = process_rule(child, project_vars, views_project_vars, sql_query, triple_patterns, bgp)

    elif rule.data == 'triplesblock':
        triplesblock_query, project_vars, triple_patterns = build_triple_pattern_query(rule.children[0], triple_patterns, bgp)
        for var in project_vars:
            if var in views_project_vars:
                views_project_vars[var].append(view_alias)
            else:
                views_project_vars[var] = [view_alias]

        sql_query += f"( {triplesblock_query} )"

        for child in rule.children[1:]:
            outer_sql_query, outer_view_alias, outer_project_vars, triple_patterns = process_rule(child, project_vars, views_project_vars, sql_query, triple_patterns, bgp)

            project_vars_intersection = project_vars.intersection(outer_project_vars)
            if project_vars_intersection:
                sql_query = f"{outer_sql_query} AS {outer_view_alias}\nINNER JOIN\n{sql_query} AS {view_alias} ON "
                while project_vars_intersection:
                    join_var = project_vars_intersection.pop()

                    if outer_view_alias not in views_project_vars[join_var]:
                        for v in views_project_vars[join_var]:
                            if v != outer_view_alias and v != view_alias:
                                outer_view_alias = v

                    sql_query += f"{outer_view_alias}.{join_var}={view_alias}.{join_var} AND "  # AND join with all views_project_vars?
                sql_query = f"( {sql_query[:-5]} )"
            else:
                sql_query = f"{outer_sql_query} AS {outer_view_alias}\nCROSS JOIN\n{sql_query} "

            project_vars.update(outer_project_vars)

    elif rule.data == 'filter':
        sql_query += build_filter_selection(rule.children[0])

    elif rule.data == 'optionalgraphpattern':
        for child in rule.children:
            outer_sql_query, outer_view_alias, outer_project_vars, triple_patterns = process_rule(child, project_vars, views_project_vars, sql_query, triple_patterns, bgp)

    elif rule.data == 'grouporuniongraphpattern':
        for child in rule.children:
            outer_sql_query, outer_view_alias, outer_project_vars, triple_patterns = process_rule(child, project_vars, views_project_vars, sql_query, triple_patterns, bgp)

    return sql_query, view_alias, project_vars, triple_patterns


def retrieve_triple_patterns(sparql_query, sparql_parser):
    tree = sparql_parser.parse(sparql_query)
    sparql_query = TreeToSPARQL().transform(tree)

    prologue = sparql_query[1][0]
    select_query = sparql_query[1][1]

    where_clause = select_query.children[1].children[0]

    where_sql_query, view_alias, project_vars, triple_patterns = process_rule(where_clause, set(), dict(), '')

    ##### PROLOGUE

    for prefix, namespace in prologue.children:
        for i, tp in enumerate(triple_patterns):
            for j, pos in enumerate(tp):
                if pos.startswith(f"{prefix}:"):
                    triple_patterns[i][j] = namespace + pos.replace(f"{prefix}:", '')
                elif pos.startswith('<') or pos.startswith('"'):
                    triple_patterns[i][j] = triple_patterns[i][j][1:-1]


    return pd.DataFrame(triple_patterns, columns=['s', 'p', 'o', 'bgp'])


def simplify_mapping(asserted_mapping_df, sparql_query, sparql_parser):
    triple_patterns_df = retrieve_triple_patterns(sparql_query, sparql_parser)


    simplified_df = asserted_mapping_df
    simplified_df['is_used'] = False

    ###############################################################################
    ######################## UNBOUNDED SUBJECTS ###################################
    ###############################################################################

    subject_groups_df = [group for _, group in asserted_mapping_df.groupby(by='subject_invariant')]

    # structure for subject groups
    sgs = []
    for i, subject_group_df in enumerate(subject_groups_df):
        sg = dict()
        sg['subject_invariant'] = subject_group_df.iloc[0]['subject_invariant']
        sg['predicates'] = set(subject_group_df['predicate_map_value'])
        aux_df = subject_group_df[subject_group_df['predicate_map_value'] == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type']
        sg['classes'] = set(aux_df['object_map_value'])
        sgs.append(sg)


    star_triple_patterns_df = triple_patterns_df[triple_patterns_df['s'].str.startswith('?')]
    star_triple_patterns_df = [group for _, group in star_triple_patterns_df.groupby(by='s')]

    for star_triple_pattern_df in star_triple_patterns_df:
        all_preds_bound = True
        for pred in star_triple_pattern_df['p']:
            if pred.startswith('?'):
                all_preds_bound = False

        if all_preds_bound:
            for sg in sgs:
                stp_sg_predicate_intersection = set(star_triple_pattern_df['p']).intersection(sg['predicates'])

                # if star pattern is typed and triples map is typed check if they overlap
                if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type' in list(star_triple_pattern_df['p']):
                    if len(set(star_triple_pattern_df['o']).intersection(sg['classes'])) > 0:
                        for i, row in simplified_df.iterrows():
                            if row['subject_invariant'] == sg['subject_invariant'] and row['predicate_map_value'] in stp_sg_predicate_intersection:
                                # set to used the rules in the triples maps based on the predicates
                                simplified_df.at[i, 'is_used'] = True
                else:
                    for i, row in simplified_df.iterrows():
                        if row['subject_invariant'] == sg['subject_invariant'] and row['predicate_map_value'] in stp_sg_predicate_intersection:
                            # set to used the rules in the triples maps based on the predicates
                            simplified_df.at[i, 'is_used'] = True

        else:   # unbound predicates
            for sg in sgs:
                if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type' in list(star_triple_pattern_df['p']):
                    if len(set(star_triple_pattern_df['o']).intersection(sg['classes'])) > 0:
                        for i, row in simplified_df.iterrows():
                            if row['subject_invariant'] == sg['subject_invariant']:
                                # set to used the rules in the triples maps based on the predicates
                                simplified_df.at[i, 'is_used'] = True
                else:
                    # it is not possible to simplify mappings
                    simplified_df['is_used'] = True



    ###############################################################################
    ######################## BOUNDED SUBJECTS #####################################
    ###############################################################################

    bounded_triple_patterns_df = triple_patterns_df[~triple_patterns_df['s'].str.startswith('?')]
    for i, rule in simplified_df.iterrows():
        for j, triple_pattern in bounded_triple_patterns_df.iterrows():
            if triple_pattern['s'].startswith(rule['subject_invariant']):
                if triple_pattern['p'].startswith('?'):
                    simplified_df.at[i, 'is_used'] = True
                else:
                    if triple_pattern['p'] == rule['predicate_map_value']:
                        simplified_df.at[i, 'is_used'] = True


    simplified_df = simplified_df[simplified_df.is_used == True]

    return simplified_df
