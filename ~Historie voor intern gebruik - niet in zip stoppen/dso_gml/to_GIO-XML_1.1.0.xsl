<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fn="http://www.w3.org/2005/xpath-functions"
    xmlns:data="https://standaarden.overheid.nl/stop/imop/data/" 
    xmlns:geo="https://standaarden.overheid.nl/stop/imop/geo/" 
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns="https://standaarden.overheid.nl/lvbb/stop/aanlevering/"
    exclude-result-prefixes="xs fn data"
    version="1.0">
    
    <xsl:output method="xml" version="1.0" indent="yes" encoding="utf-8"/>
    
    <!-- schema version -->
    <xsl:param name="schemaversion" select="'1.1.0'"/>
    <xsl:param name="schemalocation" select="concat('https://standaarden.overheid.nl/lvbb/stop/aanlevering https://standaarden.overheid.nl/lvbb/',$schemaversion,'/lvbb-stop-aanlevering.xsd')"/>
    
    <!-- get filename and open gml file -->
    <xsl:param name="gml_file" select="//bestandsnaam/text()"/>
    <xsl:param name="gml" select="document(concat('file:/',$gml_file))"/>
    <!-- create xml file name -->
    <xsl:param name="output" select="concat('file:/',substring-before($gml_file,'.gml'),'.xml')"/>
    
    <!-- get parameters -->
    <xsl:param name="FRBRExpression" select="//FRBRExpression/text()"/>
    <!--<xsl:param name="FRBRWork" select="tokenize($FRBRExpression,'/nld@')[1]"/>-->
    <xsl:param name="FRBRWork" select="substring-before($FRBRExpression,'/nld@')"/>
    <xsl:param name="soortWork" select="//soortWork/text()"/>
    <xsl:param name="hash" select="//hash/text()"/>
    <xsl:param name="geboorteregeling" select="//geboorteregeling/text()"/>
    <xsl:param name="eindverantwoordelijke" select="//eindverantwoordelijke/text()"/>
    <xsl:param name="maker" select="//maker/text()"/>
    <xsl:param name="officieleTitel" select="//officieleTitel/text()"/>
    <xsl:param name="alternatieveTitel" select="//alternatieveTitel/text()"/>
    <xsl:param name="publicatieinstructie" select="//publicatieinstructie/text()"/>
    <xsl:param name="formaatInformatieobject" select="//formaatInformatieobject/text()"/>
    <xsl:param name="naamInformatieObject" select="//naamInformatieObject/text()"/>
    
    <!-- Create xml -->
    <xsl:template match="/gio">
        <AanleveringInformatieObject>
        <!--<xsl:element name="AanleveringInformatieObject" namespace="https://standaarden.overheid.nl/lvbb/stop/aanlevering/" inherit-namespaces="no">-->
<!--            <xsl:namespace name="geo">https://standaarden.overheid.nl/stop/imop/geo/</xsl:namespace>
            <xsl:namespace name="xsi">http://www.w3.org/2001/XMLSchema-instance</xsl:namespace>-->
            <xsl:attribute name="schemaversie"><xsl:value-of select="$schemaversion"/></xsl:attribute>
            <xsl:attribute name="xsi:schemaLocation"><xsl:value-of select="$schemalocation"/></xsl:attribute>
            <xsl:element name="InformatieObjectVersie">
                <xsl:element name="ExpressionIdentificatie" namespace="https://standaarden.overheid.nl/stop/imop/data/">
                    <xsl:element name="FRBRWork" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$FRBRWork"/></xsl:element>
                    <xsl:element name="FRBRExpression" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$FRBRExpression"/></xsl:element>
                    <xsl:element name="soortWork" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$soortWork"/></xsl:element>
                </xsl:element>
                <xsl:element name="InformatieObjectVersieMetadata" namespace="https://standaarden.overheid.nl/stop/imop/data/">
                    <xsl:element name="heeftGeboorteregeling"  namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$geboorteregeling"/></xsl:element>
                    <xsl:element name="heeftBestanden" namespace="https://standaarden.overheid.nl/stop/imop/data/">
                        <xsl:element name="heeftBestand" namespace="https://standaarden.overheid.nl/stop/imop/data/">
                            <xsl:element name="Bestand" namespace="https://standaarden.overheid.nl/stop/imop/data/">
                                <xsl:element name="bestandsnaam" namespace="https://standaarden.overheid.nl/stop/imop/data/">
                                    <xsl:call-template name="fileName">
                                        <xsl:with-param name="str" select="$gml_file" />
                                    </xsl:call-template>
                                </xsl:element>
                                <xsl:element name="hash" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$hash"/></xsl:element>
                            </xsl:element>
                        </xsl:element>
                    </xsl:element>
                </xsl:element>
                <xsl:element name="InformatieObjectMetadata" namespace="https://standaarden.overheid.nl/stop/imop/data/">
                    <xsl:element name="eindverantwoordelijke" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$eindverantwoordelijke"/></xsl:element>
                    <xsl:element name="maker" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$maker"/></xsl:element>
                    <xsl:element name="alternatieveTitels" namespace="https://standaarden.overheid.nl/stop/imop/data/">
                        <xsl:element name="alternatieveTitel" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$alternatieveTitel"/></xsl:element>
                    </xsl:element>
                    <xsl:element name="officieleTitel" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$officieleTitel"/></xsl:element>
                    <xsl:element name="publicatieinstructie" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$publicatieinstructie"/></xsl:element>
                    <xsl:element name="formaatInformatieobject" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$formaatInformatieobject"/></xsl:element>
                    <xsl:element name="naamInformatieObject" namespace="https://standaarden.overheid.nl/stop/imop/data/"><xsl:value-of select="$naamInformatieObject"/></xsl:element>
                </xsl:element>
            </xsl:element>
        <!--</xsl:element>-->
        </AanleveringInformatieObject>
    </xsl:template>
    
    <xsl:template name="fileName">
        <xsl:param name="str" />
        <xsl:choose>
            <xsl:when test="normalize-space(substring-after($str,'/'))">
                <xsl:call-template name="fileName">
                    <xsl:with-param name="str" select="substring-after($str,'/')" />
                </xsl:call-template>  
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$str" />
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
</xsl:stylesheet>