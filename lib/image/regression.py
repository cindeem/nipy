import copy, os, csv, string, fpformat
import numpy as N
import enthought.traits as traits
import image
from neuroimaging.reference import grid
from neuroimaging.statistics.regression import RegressionOutput
from neuroimaging.statistics import utils


class ImageRegressionOutput(RegressionOutput):
    """
    A class to output things in GLM passes through Image data. It
    uses the image\'s iterator values to output to an image.


    """

    nout = traits.Int(1)
    arraygrid = traits.Any()
    clobber = traits.false

    def __init__(self, grid, outgrid=None, **keywords):
        traits.HasTraits.__init__(self, **keywords)
        self.grid = grid
        if outgrid is None:
            self.outgrid = grid
        else:
            self.outgrid = outgrid
            
        if self.nout > 1:
            self.grid = grid.DuplicatedGrids([self.grid]*self.nout)
        if self.arraygrid is not None:
            self.img = iter(image.Image(N.zeros(self.arraygrid.shape, N.Float), grid=self.arraygrid))

    def sync_grid(self, img=None):
        """
        Synchronize an image's grid iterator to self.grid's iterator.
        """
        if img is None:
            img = self.img
        img.grid.itertype = self.grid.itertype
        img.grid.labels = self.grid.labels
        img.grid.labelset = self.grid.labelset
        iter(img)
        
    def __iter__(self):
        return self

    def next(self, data=None):
        value = self.grid.itervalue
        self.img.next(data=data, value=value)

    def extract(self, results):
        return 0.

class TContrastOutput(ImageRegressionOutput):

    contrast = traits.Any() # should really start specifying classes with traits, too
    effect = traits.true
    sd = traits.true
    t = traits.true
    outdir = traits.Str()
    ext = traits.Str('.img')
    subpath = traits.Str('contrasts')

    def __init__(self, grid, contrast, path='.', **keywords):
        ImageRegressionOutput.__init__(self, grid, **keywords)                
        self.contrast = contrast
        self.outdir = os.path.join(path, self.subpath, self.contrast.name)
        self.path = path
        self.setup_contrast()
        self.setup_output(time=self.frametimes)

    def setup_contrast(self, **extra):
        self.contrast.getmatrix(**extra)

    def setup_output(self, **extra):

        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)

        outname = os.path.join(self.outdir, 't%s' % self.ext)
        self.timg = image.Image(outname, mode='w', grid=self.outgrid,
                                clobber=self.clobber)

        self.sync_grid(img=self.timg)

        if self.effect:
            outname = os.path.join(self.outdir, 'effect%s' % self.ext)
            self.effectimg = image.Image(outname, mode='w', grid=self.outgrid,
                                         clobber=self.clobber)
            self.sync_grid(img=self.effectimg)
        if self.sd:
            outname = os.path.join(self.outdir, 'sd%s' % self.ext)
            self.sdimg = iter(image.Image(outname, mode='w', grid=self.outgrid,
                                          clobber=self.clobber))
            self.sync_grid(img=self.sdimg)


        outname = os.path.join(self.outdir, 'matrix.csv')
        outfile = file(outname, 'w')
        outfile.write(string.join([fpformat.fix(x,4) for x in self.contrast.matrix], ',') + '\n')
        outfile.close()

        outname = os.path.join(self.outdir, 'matrix.bin')
        outfile = file(outname, 'w')
        self.contrast.matrix = self.contrast.matrix.astype('<f8')
        self.contrast.matrix.tofile(outfile)
        outfile.close()

    def extract(self, results):
        return results.Tcontrast(self.contrast.matrix, sd=self.sd, t=self.t)

    def next(self, data=None):
        value = self.grid.itervalue

        self.timg.next(data=data.t, value=value)
        if self.effect:
            self.effectimg.next(data=data.effect, value=value)
        if self.sd:
            self.sdimg.next(data=data.effect, value=value)

class FContrastOutput(ImageRegressionOutput):

    contrast = traits.Any()
    outdir = traits.Str()
    ext = traits.Str('.img')
    subpath = traits.Str('contrasts')

    def __init__(self, grid, contrast, path='.', **keywords):
        ImageRegressionOutput.__init__(self, grid, **keywords)                
        self.contrast = contrast
        self.path = path
        self.outdir = os.path.join(self.path, self.subpath, self.contrast.name)
        self.setup_contrast()
        self.setup_output()

    def setup_contrast(self, **extra):
        self.contrast.getmatrix(**extra)

    def setup_output(self):

        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)

        outname = os.path.join(self.outdir, 'F%s' % self.ext)
        self.img = iter(image.Image(outname, mode='w', grid=self.outgrid,
                                    clobber=self.clobber))
        self.sync_grid()

        outname = os.path.join(self.outdir, 'matrix.csv')
        outfile = file(outname, 'w')
        writer = csv.writer(outfile)
        for row in self.contrast.matrix:
            writer.writerow([fpformat.fix(x, 4) for x in row])
        outfile.close()

        outname = os.path.join(self.outdir, 'matrix.bin')
        outfile = file(outname, 'w')
        self.contrast.matrix = self.contrast.matrix.astype('<f8')
        self.contrast.matrix.tofile(outfile)
        outfile.close()

    def extract(self, results):
        F = results.Fcontrast(self.contrast.matrix).F
        return results.Fcontrast(self.contrast.matrix).F


class ResidOutput(ImageRegressionOutput):

    outdir = traits.Str()
    ext = traits.Str('.img')
    basename = traits.Str('resid')

    def __init__(self, grid, path='.', nout=1, **keywords):
        ImageRegressionOutput.__init__(self, grid, nout=nout, **keywords)                
        self.outdir = os.path.join(path)
        self.path = path
    
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        outname = os.path.join(self.outdir, '%s%s' % (self.basename, self.ext))
        self.img = image.Image(outname, mode='w', grid=self.grid,
                               clobber=self.clobber)
        self.nout = self.grid.shape[0]
        self.sync_grid()

    def extract(self, results):
        return results.resid
    
    def next(self, data=None):
        value = self.grid.next()
        self.img.next(data=data, value=value)
