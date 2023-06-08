#This is a test
import arcpy, os, string

arcpy.env.workspace = "in_memory"

# get the input parameters
# first the input feature class for this data
inRaster = arcpy.GetParameterAsText(0)
if not inRaster:    # for debugging purposes....
    inRaster = r"Z:\lidar_resources\data\q250k\q1942\geodatabase\1942-08-56.gdb\dem01"
    #inRaster = r"D:\gistemp\MyProjects\local\lidarclip"

outRaster = arcpy.GetParameterAsText(1)
if not outRaster: # for debugging purposes.
    outRaster = r"d:\temp\rasarea"
    #outRaster = r"d:\gistemp\MyProjects\local\outRaster"
    if arcpy.Exists(outRaster): arcpy.Delete_management(outRaster)

try:
    # make sure that a license is available.
    if arcpy.CheckExtension("spatial") == "Available":
        arcpy.CheckOutExtension("spatial")
    else:
        raise "LicenseError"
    # describe the incoming raster so we know it's linear units...
    desc = arcpy.Describe(inRaster)
    inUnits = desc.spatialReference.linearUnitName
    arcpy.AddMessage("\tInput X,Y Units are " + inUnits)

    # do the unit conversion from input linear units to acres....
    if inUnits == "Meter":
        convFactor = 0.0002471054
    elif string.find(inUnits,"Foot") > -1:
        convFactor = 0.00002295684
    else:
        arcpy.AddError("Projection not set for raster - unable to calculate acres...")
        sys.exit()
    arcpy.AddMessage("Calculating true surface area...")

    # calculate the cell area from the width and height...
    cellArea = desc.MeanCellWidth * desc.MeanCellHeight

    equation = str(cellArea * convFactor) + " / cos(Degrees_Slope / 57.296)"
    arcpy.AddMessage("\tCalculating cell surface acreage based on slope using the equation - " + equation)

    cellAreaRaster = (cellArea * convFactor) / arcpy.sa.Cos(arcpy.sa.Slope(inRaster,"DEGREE","1") / 57.296)
    cellAreaRaster.save(outRaster)

    arcpy.AddMessage("\tCreated output raster. Summing areas . . .")

    # Create temporary extent rectangle
    extent_fc = os.path.basename(inRaster) + "_extent"
    corners = ["lowerLeft", "lowerRight", "upperRight", "upperLeft"]
    points = []
    r = arcpy.Raster(inRaster)
    for corner in corners:
        x = getattr(r.extent, "%s" % corner).X
        y = getattr(r.extent, "%s" % corner).Y
        points.append(arcpy.Point(x, y))
    polygon = arcpy.Polygon(arcpy.Array(points))
    if arcpy.Exists(extent_fc):
        arcpy.Delete_management(extent_fc)
    arcpy.CreateFeatureclass_management("in_memory", extent_fc, "POLYGON", "", "", "", inRaster)
    arcpy.AddField_management(extent_fc, "zone", "SHORT")
    with arcpy.da.InsertCursor(extent_fc, ["SHAPE@","zone"]) as cursor:
        row = [polygon, 1] # Create single feature with polygon = extent, zone = 1
        cursor.insertRow(row)

    # Calculate Area Sum
    out_workspace = os.path.dirname(outRaster)
    out_raster_name = os.path.basename(outRaster)
    if ".gdb" in os.path.dirname(outRaster):
        out_table_name = out_raster_name + "_sum_acres"
    else:
        if "." in out_raster_name:
            out_raster_name = out_raster_name.split(".")[0]
        out_table_name = out_raster_name + "_sum_acres.dbf"
    out_table = os.path.join(out_workspace, out_table_name)
    if arcpy.Exists(out_table):
        arcpy.AddError("Error: output sum_acres table already exists")
        exit(1)
    arcpy.sa.ZonalStatisticsAsTable(extent_fc, "zone", outRaster, out_table, "", "SUM")
    with arcpy.da.SearchCursor(out_table, "SUM") as sum_tuples:
        sum_value = str([sum_tuple[0] for sum_tuple in sum_tuples][0])
    arcpy.AddMessage("The total area is " + sum_value + " acres.")
    arcpy.AddMessage("This value is stored in the table " + out_table)
except "LicenseError":
    arcpy.AddMessage("Spatial Analyst license is unavailable")

