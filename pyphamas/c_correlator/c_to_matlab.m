% Read in C correlation file
close all;
clearvars;

filename = 'tmp3.bin';

nbins = 91;
nele = 32;
FID = fopen(filename);
params = uint32(fread(FID, 7, 'int').');
params(1:6) = params(1:6) + 1;
data = fread(FID, nele*nele*nbins*2, 'float');
fclose(FID);

data = data(1:2:end) + 1j*data(2:2:end);
Rmat = permute(reshape(data, nele, nele, nbins), [2 1 3]);
R = cell(nbins);
for b = 1:nbins
    R{b} = Rmat(:,:,b) + Rmat(:,:,b)' - diag(diag(Rmat(:,:,b)));
end

save('tmp.mat', 'R', 'params');