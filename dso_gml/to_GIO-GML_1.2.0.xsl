<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fn="http://www.w3.org/2005/xpath-functions"
    xmlns:basisgeo="http://www.geostandaarden.nl/basisgeometrie/1.0" 
    xmlns:data="https://standaarden.overheid.nl/stop/imop/data/" 
    xmlns:geo="https://standaarden.overheid.nl/stop/imop/geo/" 
    xmlns:gio="https://standaarden.overheid.nl/stop/imop/gio/" 
    xmlns:gml="http://www.opengis.net/gml/3.2" 
    xmlns:rsc="https://standaarden.overheid.nl/stop/imop/resources/"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    exclude-result-prefixes="xs fn rsc data"
    version="1.0">
    
    <xsl:output method="xml" version="1.0" indent="yes" encoding="utf-8"/>
    
    <!-- schema version -->
    <xsl:param name="schemaversion" select="'1.3.0'"/>
    <xsl:param name="schemalocation" select="concat('https://standaarden.overheid.nl/stop/imop/geo/ https://standaarden.overheid.nl/stop/',$schemaversion,'/imop-geo.xsd')"/>
    
    <xsl:param name="gml_file" select="string(//bestandsnaam/text())"/>
    <xsl:param name="gml" select="document(concat('file:/',$gml_file))"/>
    <xsl:param name="output" select="concat('file:/',substring-before($gml_file,'.gml'),'_gio.gml')"/>
    
    <xsl:param name="ids" select="/gio/ids"/> <!--lijst met guids-->
    <xsl:param name="namen" select="/gio/namen"/> <!--lijst namen met volgnummers-->
    <xsl:param name="Naam" select="/gio/naamInformatieObject/text()"/>
    <xsl:param name="FRBRExpression" select="/gio/FRBRExpression/text()"/>
    <xsl:param name="Verwijzing" select="/gio/Verwijzing/text()"/>
    <xsl:param name="Actualiteit" select="/gio/Actualiteit/text()"/>
    
    <!-- open gml and apply templates on it -->
    <xsl:template match="/gio">
        <xsl:message>gio|<xsl:value-of select="$gml_file"/></xsl:message>
        <xsl:apply-templates select="$gml/*"/>
    </xsl:template>
    
    <!--Identity template, kopieer alle inhoud -->
    <xsl:template match="@*|node()">
        <xsl:message>Identity</xsl:message>
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="//*[local-name()='FeatureCollection']">
        <xsl:message>FeatureCollection</xsl:message>
        <!-- vanwege parser in python geen xsl:element hier gebruiken, namespaces komen er anders niet in -->
        <geo:GeoInformatieObjectVaststelling>
            <xsl:attribute name="xsi:schemaLocation"><xsl:value-of select="$schemalocation"/></xsl:attribute>
            <xsl:attribute name="schemaversie"><xsl:value-of select="$schemaversion"/></xsl:attribute>
            <xsl:element name="geo:context">
                <xsl:element name="gio:GeografischeContext">
                    <xsl:element name="gio:achtergrondVerwijzing"><xsl:value-of select="$Verwijzing"/></xsl:element>
                    <xsl:element name="gio:achtergrondActualiteit"><xsl:value-of select="$Actualiteit"/></xsl:element>
                </xsl:element>
            </xsl:element>
            <xsl:element name="geo:vastgesteldeVersie">
                <xsl:element name="geo:GeoInformatieObjectVersie">
                    <xsl:variable name="FRBRWork" select="substring-before($FRBRExpression,'/nld')"/>
                    <xsl:element name="geo:FRBRWork"><xsl:value-of select="$FRBRWork"/></xsl:element>
                    <xsl:element name="geo:FRBRExpression"><xsl:value-of select="$FRBRExpression"/></xsl:element>
                    <!-- TODO: Groepen en Normen -->
                    <xsl:element name="geo:locaties">
                        <xsl:apply-templates select="@*|node()"/>
                    </xsl:element>
                </xsl:element>
            </xsl:element>
        <!--</xsl:element>-->
        </geo:GeoInformatieObjectVaststelling>
    </xsl:template>
    
    <!-- lege element teksten overslaan -->
    <xsl:template match="text()[string-length(normalize-space(.))=0]"/>
    
    <!-- gml:id uit root overslaan -->
    <xsl:template match="@gml:id"/>

    <!-- tijdelijke elementen overslaan -->
    <xsl:template match="id"/>
    <xsl:template match="Naam"/>
    <xsl:template match="FRBRExpression"/>
    <xsl:template match="Verwijzing"/>
    <xsl:template match="Actualiteit"/>
    
    <!-- xsi:schemaLocation uit root overslaan -->
    <xsl:template match="@xsi:schemaLocation"/>
    
    <!-- boundedBy overslaan -->
    <xsl:template match="//*[local-name()='boundedBy']"/>
    
    <!-- featureMember naar Locatie -->
    <xsl:template match="//*[local-name()='featureMember']">
        <xsl:message>featureMember</xsl:message>
        <!-- Bij meerdere featureMembers -->
        <xsl:variable name="pos" select="count(preceding-sibling::*[local-name()='featureMember'])+1"/>
        <xsl:variable name="id"><xsl:value-of select="$ids/*[$pos]/text()"/></xsl:variable>
        <xsl:element name="geo:Locatie">
            <xsl:variable name="LocatieNaam">
                <xsl:choose>
                    <!--<xsl:when test="./parent::node()/count(*[local-name()='featureMember'])=1">-->
                    <xsl:when test="count(./parent::node()/*[local-name()='featureMember'])=1">
                        <xsl:value-of select="$Naam"/>
                    </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="$namen/*[$pos]/text()"/>
                </xsl:otherwise>
                </xsl:choose>
            </xsl:variable>
            <xsl:element name="geo:naam"><xsl:value-of select="$LocatieNaam"/></xsl:element>
            <xsl:element name="geo:geometrie">
                <xsl:element name="basisgeo:Geometrie" namespace="http://www.geostandaarden.nl/basisgeometrie/1.0">
                    <xsl:attribute name="gml:id"><xsl:value-of select="concat('id-',$id,'-xx')"/></xsl:attribute>
                    <xsl:element name="basisgeo:id"><xsl:value-of select="$id"/></xsl:element>
                    <xsl:element name="basisgeo:geometrie">
                        <xsl:apply-templates select=".//*[local-name()='geometryProperty']/*" xpath-default-namespace="https://standaarden.overheid.nl/stop/imop/geo/"/>
                    </xsl:element>
                </xsl:element>
            </xsl:element>
        </xsl:element>
    </xsl:template>
    
</xsl:stylesheet>