# Context

As one of the [Copernicus Emergency Management Service](https://emergency.copernicus.eu/) Rapid Mapping and Risk and Recovery Mapping operators, 
[SERTIT](https://sertit.unistra.fr/) needs to deliver geoinformation (such as flood or fire delineation, landslides mapping, etc.) based on multiple EO constellations.

In rapid mapping, it is always important to have access to various sensor types, resolutions, and satellites. Indeed, SAR sensors are able to detect through clouds and during nighttime 
(which is particularly useful during flood and storm events), while optical sensors benefit from multispectral bands to better analyze and classify the crisis information.

As every minute counts in the production of geoinformation in an emergency mode, it seemed crucial to harmonize the ground on which our production tools are built, in order to make them as
sensor-agnostic as possible.

This is why SERTIT decided to decouple the sensor handling from the extraction algorithms: the latter should be able to ingest semantic bands 
(i.e. `RED` or `VV`) without worrying about how to load the specific sensor band or in what unit it is.  
The assumption was made that all the spectral bands from optical sensors could be mapped between each other, in addition to the natural mapping between SAR bands.

Thus, thanks to **EOReader**, these tools are made independent of the constellation:  
✅ the algorithm (and its developer) can focus on its core tasks (such as extraction) without taking into account the sensor characteristics 
(how to load a band, which band corresponds to which band number, …)  
✅ new sensor addition is effortless (if existing in **EOReader**) and requires no algorithm modification  
✅ maintenance is simplified and the code quality is significantly improved  
✅ testing is also simplified as the sensor-related parts are tested in the EOReader library  

However, keep in mind that the support of all the constellations used in CEMS is done in the best effort mode, especially for commercial data.
Indeed, we may not have faced every product type, sensor mode or order configuration, so some details may be missing.
If this happens to you, do not hesitate to make a PR or write an issue about that!
