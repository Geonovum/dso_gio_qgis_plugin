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
    <xsl:param name="schemaversion" select="'1.0.4'"/>
    <xsl:param name="schemalocation" select="'https://standaarden.overheid.nl/stop/imop/geo/ https://standaarden.overheid.nl/stop/1.0.4/imop-geo.xsd'"/>
    
    <xsl:param name="gml_file" select="string(//bestandsnaam/text())"/>
    <xsl:param name="gml" select="document(concat('file:/',$gml_file))"/>
    <xsl:param name="output" select="concat('file:/',substring-before($gml_file,'.gml'),'_gio.gml')"/>
    
    <!--<xsl:param name="GUID" select="substring-after(/element()/@gml:id,'-')"/>-->
    <xsl:param name="id" select="//id/text()"/>
    <xsl:param name="Naam" select="//naamInformatieObject/text()"/>
    <xsl:param name="FRBRExpression" select="//FRBRExpression/text()"/>
    <xsl:param name="Verwijzing" select="//Verwijzing/text()"/>
    <xsl:param name="Actualiteit" select="//Actualiteit/text()"/>
    
    <!-- open gml and apply templates on it -->
    <xsl:template match="/gio">
        <xsl:apply-templates select="$gml/*"/>
    </xsl:template>
    
    <!--Identity template, kopieer alle inhoud -->
    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="//*[local-name()='FeatureCollection']">
        <!-- vanwege parser in python geen xsl:element hier gebruiken, namespaces komen er anders niet in -->
        <geo:GeoInformatieObjectVaststelling>
        <!--<xsl:element name="geo:GeoInformatieObjectVaststelling">-->
<!--            <xsl:namespace name="geo">https://standaarden.overheid.nl/stop/imop/geo/</xsl:namespace>
            <xsl:namespace name="gio">https://standaarden.overheid.nl/stop/imop/gio/</xsl:namespace>
            <xsl:namespace name="basisgeo">http://www.geostandaarden.nl/basisgeometrie/1.0</xsl:namespace>
            <xsl:namespace name="gml">http://www.opengis.net/gml/3.2</xsl:namespace>
            <xsl:namespace name="xsi">http://www.w3.org/2001/XMLSchema-instance</xsl:namespace>-->
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
        <xsl:element name="geo:Locatie">
                <xsl:apply-templates select="@*|node()"/>
        </xsl:element>
    </xsl:template>
    
    <!-- 'geometrie' veld -->
    <xsl:template match="//*[local-name()='geometrie']">
        <xsl:element name="geo:naam"><xsl:value-of select="$Naam"/></xsl:element>
        <xsl:element name="geo:geometrie">
            <xsl:element name="basisgeo:Geometrie" namespace="http://www.geostandaarden.nl/basisgeometrie/1.0">
                <xsl:attribute name="gml:id"><xsl:value-of select="concat('id-',$id,'-xx')"/></xsl:attribute>
                <xsl:element name="basisgeo:id">
                    <xsl:choose>
                        <xsl:when test="./*[local-name()='id']/text()"><xsl:value-of select="./*[local-name()='id']/text()"/></xsl:when>
                        <xsl:otherwise><xsl:value-of select="$id"/></xsl:otherwise>
                    </xsl:choose>
                </xsl:element>
                <xsl:element name="basisgeo:geometrie">
                    <xsl:apply-templates select="./*[local-name()='geometryProperty']/*" xpath-default-namespace="https://standaarden.overheid.nl/stop/imop/geo/"/>
                </xsl:element>
            </xsl:element>
        </xsl:element>
    </xsl:template>
    
    <!--<xsl:template match="/*[@srsName]">
        <xsl:attribute name="gml:id"><xsl:value-of select="concat('id-',$id)"/></xsl:attribute>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:template>-->
</xsl:stylesheet>